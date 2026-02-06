# common.mk - Shared variables and utilities for Kamiwaza Extensions
#
# This file contains:
# - Color definitions for terminal output
# - Common variables
# - Shared utility functions

ifndef _COMMON_MK_
_COMMON_MK_ := 1

# ==============================================================================
# Environment File Loading
# ==============================================================================

# Preserve AWS_PROFILE from the environment so it isn't overridden by .env
AWS_PROFILE_ENV := $(AWS_PROFILE)

# Load .env file if it exists (exports variables to environment)
# Note: We explicitly unexport guard variables to prevent submake issues
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Unexport include guard variables so submakes can define their own targets
unexport _COMMON_MK_ _BUILD_MK_ _QUALITY_MK_ _DISCOVERY_MK_ _METADATA_MK_ _TEMPLATES_MK_ _DEV_MK_ _DEMO_MK_ _HELP_MK_

# Restore AWS_PROFILE from the environment if it was set at invocation
ifneq ($(strip $(AWS_PROFILE_ENV)),)
    AWS_PROFILE := $(AWS_PROFILE_ENV)
    export AWS_PROFILE
endif

# ==============================================================================
# Terminal Colors
# ==============================================================================

# Color definitions for pretty output
ifeq ($(OS),Windows_NT)
    # Windows doesn't support ANSI colors in cmd.exe
    RED :=
    GREEN :=
    YELLOW :=
    BLUE :=
    MAGENTA :=
    CYAN :=
    WHITE :=
    NC :=
    BOLD :=
    DIM :=
    RESET :=
    HEADER :=
    COMMAND :=
    ARGS :=
    COMMENT :=
else
    # ANSI color codes for Unix-like systems
    RED := \033[0;31m
    GREEN := \033[0;32m
    YELLOW := \033[0;33m
    BLUE := \033[0;34m
    MAGENTA := \033[0;35m
    CYAN := \033[0;36m
    WHITE := \033[0;37m
    NC := \033[0m  # No Color

    # Text formatting
    BOLD := \033[1m
    DIM := \033[2m
    RESET := \033[0m

    # Semantic colors for help output
    HEADER := \033[1;35m  # Bold magenta for headers
    COMMAND := \033[0m    # Default color for commands
    ARGS := \033[0;36m    # Cyan for arguments
    COMMENT := \033[2m    # Dim for comments
endif

# ==============================================================================
# Common Variables
# ==============================================================================

# Python environment
# Use virtual environment if it exists, otherwise fallback to python3
PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

# Kamiwaza connection defaults
KAMIWAZA_API_URL ?= https://localhost/api
KAMIWAZA_USERNAME ?= admin
KAMIWAZA_PASSWORD ?= kamiwaza

# Registry server defaults
PORT ?= 58888

# ==============================================================================
# Utility Functions
# ==============================================================================

# Check if a command exists
# Usage: $(call cmd_exists,command_name)
cmd_exists = $(shell command -v $(1) 2> /dev/null)

# Print a section header
# Usage: $(call print_header,Section Name)
define print_header
	@echo ""
	@echo "$(HEADER)==============================================================================$(RESET)"
	@echo "$(HEADER)$(1)$(RESET)"
	@echo "$(HEADER)==============================================================================$(RESET)"
	@echo ""
endef

# Print a subsection
# Usage: $(call print_section,Section Name)
define print_section
	@echo ""
	@echo "$(HEADER)$(1):$(RESET)"
endef

# Print success message
# Usage: $(call print_success,Message)
define print_success
	@echo "$(GREEN)✓ $(1)$(NC)"
endef

# Print error message
# Usage: $(call print_error,Message)
define print_error
	@echo "$(RED)✗ $(1)$(NC)"
endef

# Print warning message
# Usage: $(call print_warning,Message)
define print_warning
	@echo "$(YELLOW)⚠ $(1)$(NC)"
endef

endif # _COMMON_MK_
