.PHONY: venv install test lint

venv:
	python3 -m venv .venv

install:
	. .venv/bin/activate && pip install -r requirements-dev.txt

test:
	. .venv/bin/activate && pytest tests/ -v

coverage:
	. .venv/bin/activate && pytest tests/ --cov=custom_components --cov-report=term-missing --cov-report=html

run-ha:
	. .venv/bin/activate && hass --config .

lint:
	. .venv/bin/activate && ruff check custom_components tests

format:
	. .venv/bin/activate && ruff format custom_components tests
	@for file in custom_components/energy_tracker/manifest.json custom_components/energy_tracker/translations/*.json; do \
		python3 -c "import json,sys; d=json.load(open('$$file')); json.dump(d,open('$$file','w'),ensure_ascii=False,indent=2); print('',file=open('$$file','a'))" && echo "✅ $$file"; \
	done