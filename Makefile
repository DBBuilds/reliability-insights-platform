# One entry point for local work. CI runs `make check`.
NODE_OK := $(shell node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>22||(a===22&&b>=12)?0:1)' 2>/dev/null && echo yes)

.PHONY: setup api web test lint schema check clean

setup:                 ## install backend (uv) and frontend (npm) deps from the lockfiles
	cd backend && uv sync --frozen
	@[ "$(NODE_OK)" = yes ] || { echo "Node >= 22.12 required (see frontend/.nvmrc)"; exit 1; }
	cd frontend && npm ci

api:                   ## backend on :8000 with reload
	cd backend && uv run uvicorn insights.app:app --reload --port 8000 --app-dir src

web:                   ## frontend on :5173, proxies /graphql to :8000
	cd frontend && npm run dev

schema:                ## regenerate the contract and the frontend types after a schema change
	cd backend && uv run python -m insights.export_schema
	cd frontend && npm run codegen

test:
	cd backend && uv run pytest -q
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run typecheck

check: lint test       ## everything CI checks, including contract drift
	cd backend && uv run python -m insights.export_schema
	cd frontend && npm run codegen
	git diff --exit-code -- schema frontend/src/gql || { echo "Contract drift: commit the regenerated files"; exit 1; }
	cd frontend && npm run build

clean:
	rm -rf backend/.venv frontend/node_modules frontend/dist
