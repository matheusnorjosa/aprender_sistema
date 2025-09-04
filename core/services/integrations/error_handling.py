"""
Utilitários para tratamento de erros e retry logic na integração Google Calendar.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Type, Union

logger = logging.getLogger(__name__)


class GoogleCalendarError(Exception):
    """Exceção base para erros da integração Google Calendar."""

    pass


class GoogleCalendarAuthError(GoogleCalendarError):
    """Erro de autenticação com Google Calendar."""

    pass


class GoogleCalendarQuotaError(GoogleCalendarError):
    """Erro de quota excedida da API Google Calendar."""

    pass


class GoogleCalendarNotFoundError(GoogleCalendarError):
    """Evento não encontrado no Google Calendar."""

    pass


def retry_on_error(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = None,
) -> Callable:
    """
    Decorator para retry automático em caso de falhas.

    Args:
        max_attempts: Número máximo de tentativas
        delay_seconds: Delay inicial entre tentativas (em segundos)
        backoff_multiplier: Multiplicador para backoff exponencial
        exceptions: Tupla de exceções que devem triggerar retry
    """
    if exceptions is None:
        # Exceções padrão que devem ser retriadas
        exceptions = (
            ConnectionError,
            TimeoutError,
            GoogleCalendarQuotaError,
        )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay_seconds

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Última tentativa - re-raise a exceção
                        logger.error(
                            f"Falha definitiva após {max_attempts} tentativas "
                            f"na função {func.__name__}: {e}"
                        )
                        raise

                    logger.warning(
                        f"Tentativa {attempt + 1}/{max_attempts} falhou "
                        f"na função {func.__name__}: {e}. "
                        f"Tentando novamente em {current_delay}s..."
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff_multiplier

                except Exception as e:
                    # Exceções não retriáveis - falha imediata
                    logger.error(f"Erro não retriável na função {func.__name__}: {e}")
                    raise

            # Nunca deve chegar aqui, mas por segurança
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def handle_google_api_errors(func: Callable) -> Callable:
    """
    Decorator para converter erros da API Google em exceções mais específicas.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except ImportError as e:
            logger.error(f"Bibliotecas Google não instaladas: {e}")
            raise GoogleCalendarError(
                "Bibliotecas Google não instaladas. "
                "Instale: pip install google-api-python-client google-auth"
            )
        except Exception as e:
            # Verificar tipos específicos de erro da API Google
            error_message = str(e).lower()

            if "403" in error_message and (
                "quota" in error_message or "rate" in error_message
            ):
                raise GoogleCalendarQuotaError(f"Quota da API Google excedida: {e}")
            elif "401" in error_message or "authentication" in error_message:
                raise GoogleCalendarAuthError(f"Erro de autenticação Google: {e}")
            elif "404" in error_message:
                raise GoogleCalendarNotFoundError(f"Evento não encontrado: {e}")
            else:
                # Erro genérico
                raise GoogleCalendarError(f"Erro na API Google Calendar: {e}")

    return wrapper


def log_google_calendar_operation(operation_name: str):
    """
    Decorator para logging de operações do Google Calendar.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            logger.info(f"Iniciando operação Google Calendar: {operation_name}")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"Operação {operation_name} concluída com sucesso "
                    f"em {duration:.2f}s"
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Operação {operation_name} falhou após {duration:.2f}s: {e}"
                )
                raise

        return wrapper

    return decorator


def safe_google_calendar_operation(
    max_attempts: int = 3, operation_name: str = "Google Calendar"
):
    """
    Decorator combinado que aplica logging, tratamento de erros e retry.
    """

    def decorator(func: Callable) -> Callable:
        # Aplicar decorators em ordem
        decorated_func = func
        decorated_func = handle_google_api_errors(decorated_func)
        decorated_func = retry_on_error(max_attempts=max_attempts)(decorated_func)
        decorated_func = log_google_calendar_operation(operation_name)(decorated_func)
        return decorated_func

    return decorator
