pyright:
	pyright --pythonpath "$(PYRIGHT_PYTHON_PATH)" robot
format:
	ruff format robot
