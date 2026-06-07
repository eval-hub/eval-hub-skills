SKILL_NAMES := evalhub evalhub-discovery evalhub-eval evalhub-jobs
SKILL_NAME  := evalhub
SKILL_DIR   := $(CURDIR)/$(SKILL_NAME)
TARGET_DIR  := $(HOME)/.claude/skills/$(SKILL_NAME)

.PHONY: help install install-all uninstall uninstall-all update update-all check lint test

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install the primary evalhub skill into ~/.claude/skills/ (symlink)
	@if [ -e "$(TARGET_DIR)" ]; then \
		echo "Error: $(TARGET_DIR) already exists. Use 'make update' or 'make uninstall' first."; \
		exit 1; \
	fi
	@mkdir -p "$(HOME)/.claude/skills"
	@ln -s "$(SKILL_DIR)" "$(TARGET_DIR)"
	@echo "Installed $(SKILL_NAME) → $(TARGET_DIR)"

install-all: ## Install all skills (evalhub, evalhub-discovery, evalhub-eval, evalhub-jobs)
	@mkdir -p "$(HOME)/.claude/skills"
	@for skill in $(SKILL_NAMES); do \
		src="$(CURDIR)/$$skill"; \
		dst="$(HOME)/.claude/skills/$$skill"; \
		if [ -e "$$dst" ]; then \
			echo "Skip $$skill (already installed at $$dst)"; \
		else \
			ln -s "$$src" "$$dst"; \
			echo "Installed $$skill → $$dst"; \
		fi \
	done

uninstall: ## Remove the primary evalhub skill from ~/.claude/skills/
	@if [ -L "$(TARGET_DIR)" ]; then \
		rm "$(TARGET_DIR)"; \
		echo "Removed symlink $(TARGET_DIR)"; \
	elif [ -d "$(TARGET_DIR)" ]; then \
		rm -rf "$(TARGET_DIR)"; \
		echo "Removed directory $(TARGET_DIR)"; \
	else \
		echo "Nothing to remove at $(TARGET_DIR)"; \
	fi

uninstall-all: ## Remove all skills from ~/.claude/skills/
	@for skill in $(SKILL_NAMES); do \
		dst="$(HOME)/.claude/skills/$$skill"; \
		if [ -L "$$dst" ]; then \
			rm "$$dst"; echo "Removed symlink $$dst"; \
		elif [ -d "$$dst" ]; then \
			rm -rf "$$dst"; echo "Removed directory $$dst"; \
		fi \
	done

update: uninstall install ## Update the primary evalhub skill (re-link)

update-all: uninstall-all install-all ## Update all skills (re-link)

lint: ## Lint Python scripts (ruff), shell scripts (shellcheck), and SKILL.md files (skillsaw)
	uvx ruff check evalhub/scripts/
	uvx ruff format --check evalhub/scripts/
	shellcheck test-skill.sh
	uvx skillsaw lint evalhub/SKILL.md evalhub-discovery/SKILL.md evalhub-eval/SKILL.md evalhub-jobs/SKILL.md

test: ## Run unit tests (no live service required)
	pytest tests/ -v

check: ## Validate skill structure
	@test -f "$(SKILL_DIR)/SKILL.md" || { echo "Error: SKILL.md not found in $(SKILL_DIR)"; exit 1; }
	@test -d "$(SKILL_DIR)/scripts" || { echo "Error: scripts/ not found in $(SKILL_DIR)"; exit 1; }
	@echo "Skill structure is valid:"
	@echo "  SKILL.md: OK"
	@echo "  scripts/: $$(ls $(SKILL_DIR)/scripts/*.py 2>/dev/null | wc -l) scripts"
	@echo "  references/: $$(ls $(SKILL_DIR)/references/*.md 2>/dev/null | wc -l) files"
	@echo "  assets/: $$(ls $(SKILL_DIR)/assets/* 2>/dev/null | wc -l) files"
