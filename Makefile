.PHONY: install backend frontend dev test bench

install:
	python3 -m pip install -r requirements.txt
	cd frontend && npm install

backend:
	python3 main.py

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run in two terminals:"
	@echo "  make backend"
	@echo "  make frontend"
	@echo ""
	@echo "Backend docs: http://localhost:8000/docs"
	@echo "Frontend:     http://localhost:5173"

test:
	python3 -m pytest tests/ -v

bench:
	python3 scripts/benchmark.py
