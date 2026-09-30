"""Shared errors raised by CaseCopilot-backed services."""


class CaseCopilotQuotaError(RuntimeError):
    pass


class CaseCopilotAuthenticationError(RuntimeError):
    pass


class CaseCopilotProviderError(RuntimeError):
    pass


class CaseCopilotProviderUnavailableError(CaseCopilotProviderError):
    """The upstream model provider could not be reached."""


class CaseCopilotResponseError(CaseCopilotProviderError):
    """The provider returned data that did not satisfy our contract."""
