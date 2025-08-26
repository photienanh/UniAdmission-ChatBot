import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Tắt INFO, WARNING, ERROR logs
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Tắt oneDNN warnings

import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Import và config TensorFlow để tắt tất cả warnings
try:
    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
except ImportError:
    pass  # TensorFlow not installed

from .server import *
from .database import *
from .llm import *
from .kaggle import *