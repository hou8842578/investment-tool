PYTHON ?= python3
PORT ?= 5000

.PHONY: run dev test wsgi init-prod

run:
	$(PYTHON) app.py

dev:
	INVEST_PORT=$(PORT) $(PYTHON) app.py

test:
	$(PYTHON) -m unittest discover -s tests -v

wsgi:
	gunicorn -w 2 -b 0.0.0.0:$(PORT) wsgi:app

init-prod:
	$(PYTHON) init_production_db.py $(ARGS)
