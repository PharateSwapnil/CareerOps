"""Central registry of available JobProvider implementations.

Milestone 2 will add real providers here (Greenhouse, Lever, Ashby, RSS...).
"""
from app.providers.job_providers.adzuna_provider import AdzunaJobProvider
from app.providers.job_providers.arbeitnow_provider import ArbeitnowJobProvider
from app.providers.job_providers.ashby_provider import AshbyJobProvider
from app.providers.job_providers.base import JobProvider
from app.providers.job_providers.greenhouse_provider import GreenhouseJobProvider
from app.providers.job_providers.jobicy_provider import JobicyJobProvider
from app.providers.job_providers.lever_provider import LeverJobProvider
from app.providers.job_providers.remoteco_provider import RemoteCoJobProvider
from app.providers.job_providers.remoteok_provider import RemoteOKJobProvider
from app.providers.job_providers.remotive_provider import RemotiveJobProvider
from app.providers.job_providers.stub_provider import StubJobProvider
from app.providers.job_providers.weworkremotely_provider import WeWorkRemotelyJobProvider

_REGISTRY: dict[str, JobProvider] = {
    "stub": StubJobProvider(),
    "greenhouse": GreenhouseJobProvider(),
    "arbeitnow": ArbeitnowJobProvider(),
    "remotive": RemotiveJobProvider(),
    "remoteok": RemoteOKJobProvider(),
    "lever": LeverJobProvider(),
    "ashby": AshbyJobProvider(),
    "jobicy": JobicyJobProvider(),
    "weworkremotely": WeWorkRemotelyJobProvider(),
    "adzuna": AdzunaJobProvider(),
    "remoteco": RemoteCoJobProvider(),
}


def get_provider(name: str) -> JobProvider:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown job provider: {name}") from exc


def list_providers() -> list[str]:
    return list(_REGISTRY.keys())
