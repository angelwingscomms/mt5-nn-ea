#ifndef MODEL_USE_ATR_RISK
#define MODEL_USE_ATR_RISK 1
#endif

#ifndef MODEL_USE_FIXED_TIME_BARS
#define MODEL_USE_FIXED_TIME_BARS 0
#endif

#ifndef MODEL_USE_MINIROCKET
#define MODEL_USE_MINIROCKET 0
#endif

#ifndef PRIMARY_CONFIDENCE
#define PRIMARY_CONFIDENCE 0.60
#endif

float medians[MODEL_FEATURE_COUNT] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
float iqrs[MODEL_FEATURE_COUNT] = {1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
