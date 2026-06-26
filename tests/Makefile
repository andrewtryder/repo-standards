REPO_ROOT := $(abspath ..)
TESTS_DIR := $(abspath .)
IMAGE := repo-standards-harness:latest
WORK_DIR := $(TESTS_DIR)/.work
ACT_EVENT := $(TESTS_DIR)/harness/events/push.json
STANDARDS_REF := andrewtryder/repo-standards@v1.0.0

.PHONY: build test-fixtures test-fixtures-offline test-act test clean

build:
	docker build -t $(IMAGE) -f Dockerfile .

test-fixtures:
	docker run --rm --network host \
		-v "$(REPO_ROOT):/standards:ro" \
		-v "$(TESTS_DIR):/tests:ro" \
		$(IMAGE) \
		python3 /tests/harness/run_fixtures.py \
			--standards /standards \
			--tests-dir /tests

test-fixtures-offline:
	python3 harness/run_fixtures.py \
		--standards "$(REPO_ROOT)" \
		--tests-dir "$(TESTS_DIR)" \
		--skip-assess \
		--skip-rulesync

test-act:
	@test -n "$(FIXTURE)" || (echo "Usage: make test-act FIXTURE=<name>"; exit 1)
	@command -v act >/dev/null 2>&1 || (echo "act is required: brew install act"; exit 1)
	@mkdir -p "$(WORK_DIR)/$(FIXTURE)"
	python3 harness/run_fixtures.py \
		--standards "$(REPO_ROOT)" \
		--tests-dir "$(TESTS_DIR)" \
		--fixture "$(FIXTURE)" \
		--workdir "$(WORK_DIR)/$(FIXTURE)" \
		--skip-assess \
		--skip-rulesync \
		--keep-workdir
	cd "$(WORK_DIR)/$(FIXTURE)" && act push \
		-W .github/workflows/ci.yml \
		--eventpath "$(ACT_EVENT)" \
		--local-repository "$(STANDARDS_REF)=$(REPO_ROOT)" \
		-s GITHUB_TOKEN=dummy \
		--bind

test: test-fixtures

clean:
	rm -rf "$(WORK_DIR)"
	-docker rmi $(IMAGE) 2>/dev/null || true
