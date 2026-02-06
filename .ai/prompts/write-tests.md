# Write Tests

VARIABLES:
- FILE_PATH: {file-to-test}
- TYPE: {unit|integration}
- SCOPE: {function|class|module}

TEST_STRUCTURE:
```python
# tests/test_{filename}.py
import pytest
from unittest.mock import patch, MagicMock

def test_{function}_success():
    """Test success case"""
    # Arrange
    # Act
    # Assert

def test_{function}_error():
    """Test error case"""
    with pytest.raises(Exception):
        # Test

@pytest.mark.parametrize("input,expected", [
    (val1, result1),
    (val2, result2)
])
def test_{function}_variations(input, expected):
    assert function(input) == expected
```

MOCK_PATTERNS:
```python
# Mock Kamiwaza LLM
with patch('openai.AsyncOpenAI') as mock:
    mock.return_value.chat.completions.create.return_value.choices[0].message.content = "response"

# Mock database
@pytest.fixture
def mock_db():
    db = MagicMock()
    yield db
```

RUN_TESTS:
```bash
make test TYPE={extension-type} NAME={extension-name}
pytest tests/test_{filename}.py
```