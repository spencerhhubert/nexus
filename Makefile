check:
	pyright --pythonpath "$(MY_PYTHON_PATH)" robot
format:
	ruff format robot
vulture:
	$(MY_PYTHON_PATH) -m vulture robot
migrate:
	./robot/run_script.sh robot/storage/sqlite3/migrate.py
db:
	sqlite3 database.db
conveyor:
	./robot/run.sh --disable classification feeder_conveyor vibration_hopper -y --dump --profile --use_prev_bin_state
feeder:
	./robot/run.sh --disable main_conveyor classification -y --dump --preview --use_prev_bin_state
run-nothing:
	./robot/run.sh --disable main_conveyor feeder_conveyor vibration_hopper classification -y --dump --use_prev_bin_state
run:
	./robot/run.sh -y --dump --use_prev_bin_state
rm-tmp:
	find robot -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf robot/.tmp
