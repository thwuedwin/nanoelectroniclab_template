# lab_utils/paths.py
from pathlib import Path

# 取得這個檔案所在的目錄，並往上跳一層回到根目錄
# 結構：lab_template/lab_utils/paths.py -> parent(lab_utils) -> parent(lab_template)
ROOT_DIR = Path(__file__).resolve().parent.parent

# 定義常用的子目錄，方便大家使用
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
DRIVER_DIR = ROOT_DIR / "drivers"

# 自動檢查目錄是否存在，不存在就建立（例如 data 資料夾）
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_BLUEFORS = str((CONFIG_DIR / "conf_bluefors.yaml").resolve())