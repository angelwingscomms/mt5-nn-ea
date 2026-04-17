from __future__ import annotations

from .shared import *  # noqa: F401,F403

def load_chronos_bolt_barrier_model(
    *,
    device: torch.device,
    model_id: str,
    median: Sequence[float],
    iqr: Sequence[float],
    feature_columns: Sequence[str],
    prediction_length: int,
    use_atr_risk: bool,
    label_tp_multiplier: float,
    label_sl_multiplier: float,
    context_tail_lengths: Sequence[int] | None = None,
) -> ChronosBoltBarrierClassifier:
    if not use_atr_risk:
        raise ValueError(
            "Chronos-Bolt backend currently supports ATR-based label risk only. "
            "Fixed-risk labels require absolute price scale, which is not available in the exported MT5 feature tensor."
        )

    try:
        from chronos import BaseChronosPipeline
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Chronos-Bolt backend requires the official `chronos-forecasting` package. "
            "Install dependencies from requirements.txt and rerun `nn.py --chronos-bolt`."
        ) from exc

    load_kwargs: dict[str, object] = {
        "device_map": device.type,
        "low_cpu_mem_usage": True,
    }
    if device.type == "cuda":
        load_kwargs["dtype"] = torch.bfloat16
    else:
        load_kwargs["dtype"] = torch.float32

    try:
        pipeline = BaseChronosPipeline.from_pretrained(model_id, **load_kwargs)
    except OSError as exc:
        message = str(exc).lower()
        if "paging file is too small" in message:
            raise RuntimeError(
                f"Loading {model_id} failed because Windows reported that the paging file is too small. "
                "Chronos-Bolt is much lighter than Chronos-2, but this machine still needs a larger page file or more free RAM/swap "
                "for the checkpoint load to complete."
            ) from exc
        raise RuntimeError(f"Failed to load {model_id}: {exc}") from exc

    bolt_model = pipeline.model.to(device).eval()
    if hasattr(bolt_model, "instance_norm"):
        original_instance_norm = bolt_model.instance_norm
        bolt_model.instance_norm = OnnxSafeInstanceNorm(
            eps=float(getattr(original_instance_norm, "eps", 1e-5)),
            use_arcsinh=bool(getattr(original_instance_norm, "use_arcsinh", False)),
        )
    if hasattr(bolt_model, "patch"):
        original_patch = bolt_model.patch
        bolt_model.patch = OnnxSafePatch(
            patch_size=int(getattr(original_patch, "patch_size", 0)),
            patch_stride=int(getattr(original_patch, "patch_stride", 0)),
        )
    for parameter in bolt_model.parameters():
        parameter.requires_grad_(False)

    return ChronosBoltBarrierClassifier(
        bolt_model=bolt_model,
        quantile_levels=tuple(pipeline.quantiles),
        median=median,
        iqr=iqr,
        feature_columns=tuple(feature_columns),
        prediction_length=prediction_length,
        label_tp_multiplier=label_tp_multiplier,
        label_sl_multiplier=label_sl_multiplier,
        context_tail_lengths=context_tail_lengths,
    )
