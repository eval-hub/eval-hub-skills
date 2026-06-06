SKILL_NAME := evalhub
SKILL_DIR  := $(CURDIR)/$(SKILL_NAME)
TARGET_DIR := $(HOME)/.claude/skills/$(SKILL_NAME)

.PHONY: help install uninstall update check lint test

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install the skill into ~/.claude/skills/ (symlink)
	@if [ -e "$(TARGET_DIR)" ]; then \
		echo "Error: $(TARGET_DIR) already exists. Use 'make update' or 'make uninstall' first."; \
		exit 1; \
	fi
	@mkdir -p "$(HOME)/.claude/skills"
	@ln -s "$(SKILL_DIR)" "$(TARGET_DIR)"
	@echo "Installed $(SKILL_NAME) → $(TARGET_DIR)"

uninstall: ## Remove the skill from ~/.claude/skills/
	@if [ -L "$(TARGET_DIR)" ]; then \
		rm "$(TARGET_DIR)"; \
		echo "Removed symlink $(TARGET_DIR)"; \
	elif [ -d "$(TARGET_DIR)" ]; then \
		rm -rf "$(TARGET_DIR)"; \
		echo "Removed directory $(TARGET_DIR)"; \
	else \
		echo "Nothing to remove at $(TARGET_DIR)"; \
	fi

update: uninstall install ## Update the skill (re-link)

lint: ## Lint Python scripts (ruff) and shell scripts (shellcheck)
	uvx ruff check evalhub/scripts/
	uvx ruff format --check evalhub/scripts/
	shellcheck test-skill.sh

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
