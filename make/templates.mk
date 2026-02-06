# templates.mk - Template management commands
#
# Commands for managing templates with Kamiwaza deployment
# Requires running Kamiwaza (default: KAMIWAZA_API_URL)

ifndef _TEMPLATES_MK_
_TEMPLATES_MK_ := 1

# ==============================================================================
# Template Management (requires running Kamiwaza)
# ==============================================================================

# Listing templates (read from Kamiwaza)
.PHONY: templates-list
templates-list: ## List all available templates from Kamiwaza
	$(call print_section,Listing all templates from Kamiwaza)
	@$(PYTHON) scripts/manage-templates.py list all

.PHONY: templates-list-apps
templates-list-apps: ## List available app templates from Kamiwaza
	@$(PYTHON) scripts/manage-templates.py list apps

.PHONY: templates-list-tools
templates-list-tools: ## List available tool templates from Kamiwaza
	@$(PYTHON) scripts/manage-templates.py list tools

.PHONY: templates-list-services
templates-list-services: ## List available service templates from Kamiwaza
	@$(PYTHON) scripts/manage-templates.py list services

.PHONY: templates-list-deployments
templates-list-deployments: ## List current deployments from Kamiwaza
	@$(PYTHON) scripts/manage-templates.py list deployments

# Pushing templates (push to Kamiwaza instance)
# Set KAMIWAZA_VERIFY_SSL=false for self-signed certificates
# Set KAMIWAZA_USERNAME and KAMIWAZA_PASSWORD for authentication
.PHONY: kamiwaza-push
kamiwaza-push: build-registry ## Push local app/service/tool template to Kamiwaza instance TYPE={app|service|tool} NAME={name}
ifndef TYPE
	$(error TYPE is required: make kamiwaza-push TYPE=app NAME=my-app)
endif
ifneq ($(filter $(TYPE),app service tool),$(TYPE))
	$(error TYPE must be 'app', 'service', or 'tool': make kamiwaza-push TYPE=app NAME=my-app)
endif
ifndef NAME
	$(error NAME is required: make kamiwaza-push TYPE=app NAME=my-app)
endif
	$(call print_section,Pushing $(TYPE) template '$(NAME)' to Kamiwaza)
	@KAMIWAZA_VERIFY_SSL=false $(PYTHON) scripts/manage-templates.py \
		--username $(KAMIWAZA_USERNAME) --password $(KAMIWAZA_PASSWORD) \
		garden-push $(TYPE) $(NAME) $(if $(strip $(TEMPLATE_ID)),--template-id $(TEMPLATE_ID),)

.PHONY: kamiwaza-list
kamiwaza-list: ## List app templates on Kamiwaza instance
	$(call print_section,Listing Kamiwaza templates)
	@KAMIWAZA_VERIFY_SSL=false $(PYTHON) scripts/manage-templates.py \
		--username $(KAMIWAZA_USERNAME) --password $(KAMIWAZA_PASSWORD) \
		garden-list $(if $(FORMAT),--format $(FORMAT),)

# Inspecting templates
.PHONY: templates-inspect
templates-inspect: ## Inspect template details from Kamiwaza TYPE={app|service|tool} NAME={name}
ifndef TYPE
	$(error TYPE is required: make templates-inspect TYPE=app NAME=my-app)
endif
ifndef NAME
	$(error NAME is required: make templates-inspect TYPE=app NAME=my-app)
endif
	$(call print_section,Inspecting $(TYPE) template '$(NAME)')
	@$(PYTHON) scripts/manage-templates.py inspect $(TYPE) $(NAME)

endif # _TEMPLATES_MK_
