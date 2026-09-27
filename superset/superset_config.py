#import os

# 1. Ativa a funcionalidade de Alertas e Relatórios na interface
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
}

# # 2. Configuração necessária para habilitar o motor de agendamento de Alertas
# REDIS_HOST = os.getenv("REDIS_HOST", "redis")
# REDIS_PORT = os.getenv("REDIS_PORT", "6379")
# CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
# CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

# class CeleryConfig:
#     broker_url = CELERY_BROKER_URL
#     result_backend = CELERY_RESULT_BACKEND

# CELERY_CONFIG = CeleryConfig