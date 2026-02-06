# AI Assistant Integration - Kamiwaza Extensions

CONTEXT: Rules-as-Code for Kamiwaza extension development
TARGET: AI assistants (Claude, Cursor, Copilot, etc.)

## Structure
```
.ai/
├── rules/              # Development standards
│   ├── architecture.md # Extension patterns, Docker, MCP
│   ├── python-standards.md # Python/FastAPI/async patterns
│   ├── development-lifecycle.md # CI pipeline, release workflow
│   ├── testing.md     # Validation requirements
│   ├── style.md       # Code limits, principles
│   └── tool-usage.md  # Shell tools, MCPs (ast-grep, gh, context7)
├── prompts/           # Task templates
│   ├── new-app.md     # Create app: NAME, TYPE, STACK, DESCRIPTION
│   ├── new-tool.md    # Create tool: NAME, DESCRIPTION, FUNCTIONS
│   ├── new-service.md # Create service: NAME, DESCRIPTION, STACK
│   ├── add-endpoint.md # Add API: ENDPOINT, METHOD, MODEL
│   ├── validate-extension.md # Validate: TYPE, NAME
│   └── write-tests.md # Write tests: TYPE, SCOPE
└── knowledge/         # Patterns
    ├── successful/    # Working patterns
    │   ├── app-patterns.md    # Multi-service apps
    │   └── mcp-patterns.md    # MCP tools
    └── failures/      # Known issues
        ├── docker-gotchas.md  # Docker issues
        └── appgarden-limits.md # App Garden restrictions
```

## Usage
REFERENCE: @.ai/{category}/{file}.md
EXAMPLE: Follow @.ai/prompts/new-app.md with NAME=my-app

## Integration
- CLAUDE.md: Repository overview, make commands
- .ai/rules/: Concrete standards
- .ai/prompts/: Task templates with variables
- .ai/knowledge/: Pattern examples

## Key Files
- architecture.md: Extension structure, template variables, Docker patterns
- python-standards.md: FastAPI, MCP server patterns
- development-lifecycle.md: CI/release pipeline (build→test→sync→validate→registry→push)
- testing.md: Test patterns, validation workflow
- tool-usage.md: Shell tools (ast-grep, fd, rg, gh), MCPs (context7, playwright)
- new-app.md: App creation template
- new-tool.md: Tool creation template
- new-service.md: Service creation template
- mcp-patterns.md: MCP implementation examples
