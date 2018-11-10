init:
	pip install pip pipenv
	pipenv lock
	pipenv install --dev
lint:
	pipenv run flake8 pymyq
	pipenv run pydocstyle pymyq
	pipenv run pylint pymyq
publish:
	pipenv run python setup.py sdist bdist_wheel
	pipenv run twine upload dist/*
	rm -rf dist/ build/ .egg simplisafe_python.egg-info/
typing:
	pipenv run mypy --ignore-missing-imports pymyq
