"""用 run_id 從 QCoDeS 資料庫讀取量測資料並存成 CSV（手動補匯用）。"""

import qcodes as qc
from qcodes.dataset import initialise_or_create_database_at, load_by_run_spec

from lab_utils.live_plotting.csv_export import default_csv_path, export_dataset_to_csv
from lab_utils.paths import DATA_DIR

# --- 修改這裡 ---
user = "edwin"
run_id = 13
# ---------------

user_dir = DATA_DIR / user
db_path = user_dir / "qcodes.db"

qc.config.user.mainfolder = user_dir
initialise_or_create_database_at(db_path)

dataset = load_by_run_spec(captured_run_id=run_id, read_only=True)
csv_path = export_dataset_to_csv(dataset, default_csv_path(user, run_id))

print(f"Saved: {csv_path}")
