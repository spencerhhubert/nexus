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
	./robot/run.sh --disable feeder_conveyor vibration_hopper  -y --dump --preview --use_prev_bin_state
run:
	./robot/run.sh -y --dump --preview --use_prev_bin_state
