from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from tradebot.models.sequence.causal_conv1d import CausalConv1d
from tradebot.models.sequence.sequence_attention_block import SequenceAttentionBlock
from tradebot.models.sequence.sequence_instance_norm import SequenceInstanceNorm
from tradebot.models.sequence.temporal_attention_pooling import TemporalAttentionPooling

class ScalperMicrostructureClassifier(nn.Module):
    def __init__(
        self,
        n_features: int,
        channels: int = 128,       # Increased for complex LOB/tick features
        hidden: int = 128,         
        dense_hidden: int = 64,
        n_classes: int = 3,
        attention_heads: int = 4,
        attention_dropout: float = 0.1,
        dropout: float = 0.35,     # Aggressive dropout for 9-sec noise
    ):
        super().__init__()
        
        self.backend_name = 'hft-tcn-bigru-attention'
        self.sequence_norm = SequenceInstanceNorm(n_features)
        
        # 1. Pointwise Convolution (1x1) - Learns cross-feature relationships immediately
        self.pointwise_in = nn.Conv1d(n_features, channels, kernel_size=1)
        
        # 2. Multi-scale Dilated Convolutions (TCN-style)
        # Using dilation=1 (standard), dilation=2 (skips 1 tick), dilation=4 (skips 3 ticks)
        # This captures micro-momentum across a wider 9-sec window
        self.conv_d1 = CausalConv1d(channels, channels // 3, kernel_size=2, dilation=1)
        self.conv_d2 = CausalConv1d(channels, channels // 3, kernel_size=2, dilation=2)
        self.conv_d4 = CausalConv1d(channels, channels - (2 * (channels // 3)), kernel_size=3, dilation=4)
        
        self.conv_norm = nn.LayerNorm(channels)
        self.conv_dropout = nn.Dropout(dropout)
        
        # 3. Gated Linear Unit (GLU) mechanism for the mid-convolution
        # GLU requires double the output channels to split into values and gates
        self.conv_mid_glu = CausalConv1d(channels, channels * 2, kernel_size=3)
        
        # 4. Bidirectional GRU
        self.recurrent = nn.GRU(
            input_size=channels,
            hidden_size=hidden // 2, 
            num_layers=1,
            batch_first=True,
            bidirectional=True 
        )
        self.recurrent_norm = nn.LayerNorm(hidden)
        
        self.attention = SequenceAttentionBlock(
            model_dim=hidden,
            num_heads=attention_heads,
            dropout=attention_dropout,
        )
        self.pool = TemporalAttentionPooling(hidden)
        
        # 5. Dueling Classifier (Direction + Market State)
        classifier_in_dim = (hidden * 2) + n_features
        
        # Shared dense layer
        self.dense_shared = nn.Sequential(
            nn.LayerNorm(classifier_in_dim),
            nn.Linear(classifier_in_dim, dense_hidden),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        
        # Branch A: Predicts Market State / Volatility magnitude
        self.state_branch = nn.Linear(dense_hidden, 1)
        # Branch B: Predicts Raw Direction
        self.direction_branch = nn.Linear(dense_hidden, n_classes)

    def encode_sequence(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: [batch, seq_len, features]
        normed_x = self.sequence_norm(x)
        
        # Transpose for Conv1D, which expects[batch, channels, seq_len]
        x_t = normed_x.transpose(1, 2)
        
        # Pointwise feature mixing
        x_pt = self.pointwise_in(x_t).transpose(1, 2) # Back to [batch, seq_len, channels]
        x_pt = F.gelu(x_pt)
        
        # Dilated Causal Convolutions
        x_d1 = self.conv_d1(x_pt)
        x_d2 = self.conv_d2(x_pt)
        x_d4 = self.conv_d4(x_pt)
        
        x_conv = torch.cat([x_d1, x_d2, x_d4], dim=-1)
        x_conv = self.conv_dropout(x_conv)
        
        # Gated Linear Unit Convolution
        x_glu_out = self.conv_mid_glu(x_conv)
        # GLU splits the tensor in half: one half is the feature, the other is the sigmoid gate
        x_conv = F.glu(x_glu_out, dim=-1)
        
        # Residual connection
        x_merged = self.conv_norm(x_conv + x_pt)
        
        # BiGRU & Attention
        x_rnn, _state = self.recurrent(x_merged)
        x_rnn = self.recurrent_norm(x_rnn + x_merged) 
        
        return self.attention(x_rnn)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.encode_sequence(x)
        
        pooled = self.pool(encoded)
        last_state = encoded[:, -1, :]
        last_raw_features = x[:, -1, :] 
        
        final_vector = torch.cat([last_state, pooled, last_raw_features], dim=1)
        shared_features = self.dense_shared(final_vector)
        
        # Dueling Network Output Combination
        state_val = self.state_branch(shared_features)
        direction_val = self.direction_branch(shared_features)
        
        # Aggregating them (Subtracting the mean of direction_val to center it around the state_val)
        # This allows the network to predict "0" (Neutral) confidently if state_val is low.
        q_values = state_val + (direction_val - direction_val.mean(dim=1, keepdim=True))
        
        return q_values