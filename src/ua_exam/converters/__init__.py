import abc
from typing import Dict, List, Type


class BaseConverter(abc.ABC):
    """Base class for all format converters."""

    @abc.abstractmethod
    def convert(self, input_path: str, output_path: str) -> bool:
        """Converts input_path file to output_path file.

        Args:
            input_path: Path to the input file.
            output_path: Path to the destination output file.

        Returns:
            True if successful, False otherwise.
        """
        pass


_CONVERTER_REGISTRY: Dict[str, Type[BaseConverter]] = {}


def register_converter(name: str):
    """Decorator to register a converter class."""

    def decorator(cls: Type[BaseConverter]):
        _CONVERTER_REGISTRY[name.lower()] = cls
        return cls

    return decorator


def get_converter(name: str) -> BaseConverter:
    """Returns an instance of the registered converter."""
    cls = _CONVERTER_REGISTRY.get(name.lower())
    if cls is None:
        raise ValueError(f"No converter registered for format '{name}'. Available formats: {list(_CONVERTER_REGISTRY.keys())}")
    return cls()


def get_available_formats() -> List[str]:
    """Returns list of registered format names."""
    return list(_CONVERTER_REGISTRY.keys())
