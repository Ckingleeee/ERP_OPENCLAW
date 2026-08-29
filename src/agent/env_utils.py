import os

from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY')
ALIBABA_API_KEY = os.getenv('ALIBABA_API_KEY')
ALIBABA_MODEL = os.getenv('ALIBABA_MODEL', 'qwen-plus')
ALIBABA_SEARCH_MODEL = os.getenv('ALIBABA_SEARCH_MODEL', ALIBABA_MODEL)
K2_API_KEY = os.getenv('K2_API_KEY')

K2_BASE_URL = os.getenv('K2_BASE_URL')
ALIBABA_BASE_URL = os.getenv(
    'ALIBABA_BASE_URL',
    'https://dashscope.aliyuncs.com/compatible-mode/v1',
)
MINIMAX_BASE_URL = os.getenv('MINIMAX_BASE_URL')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL')

LOCAL_BASE_URL = os.getenv('LOCAL_BASE_URL')
DAYTONA_API_KEY = os.getenv('DAYTONA_API_KEY')
DAYTONA_BASE_URL = os.getenv('DAYTONA_BASE_URL')
