"""Custom exceptions for J-Dep Analyzer."""


class JDepError(Exception):
    """Base exception for J-Dep Analyzer."""


class PomNotFoundError(JDepError):
    """Raised when a pom.xml file cannot be found."""


class PomParseError(JDepError):
    """Raised when a pom.xml file cannot be parsed."""


class PomModelError(JDepError):
    """Raised when required Maven model fields are missing or invalid."""
