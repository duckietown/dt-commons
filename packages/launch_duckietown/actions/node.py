from typing import Optional, Text, Union, Callable, Dict, Iterable

from launch import SomeSubstitutionsType, SomeEntitiesType, LaunchContext
from launch.events.process import ProcessExited
from launch.substitutions import LaunchConfiguration

from dt_node_utils.package import Package
from .python_module import PythonModule


class Node(PythonModule):

    def __init__(
            self,
            *,
            package: str,
            module: str,
            config: Optional[str] = None,
            prefix: Optional[SomeSubstitutionsType] = None,
            name: Optional[SomeSubstitutionsType] = None,
            cwd: Optional[SomeSubstitutionsType] = None,
            env: Optional[Dict[SomeSubstitutionsType, SomeSubstitutionsType]] = None,
            additional_env: Optional[Dict[SomeSubstitutionsType, SomeSubstitutionsType]] = None,
            arguments: Optional[Iterable[SomeSubstitutionsType]] = None,
            shell: bool = False,
            sigterm_timeout: SomeSubstitutionsType = LaunchConfiguration('sigterm_timeout', default=5),
            sigkill_timeout: SomeSubstitutionsType = LaunchConfiguration('sigkill_timeout', default=5),
            emulate_tty: bool = False,
            output: SomeSubstitutionsType = 'screen',
            output_format: Text = '[{this.process_description.final_name}] {line}',
            cached_output: bool = False,
            on_exit: Optional[Union[
                SomeEntitiesType,
                Callable[[ProcessExited, LaunchContext], Optional[SomeEntitiesType]]
            ]] = None,
            respawn: Union[bool, SomeSubstitutionsType] = False,
            respawn_delay: Optional[float] = None,
            respawn_max_retries: int = -1,
            runtime: str = "python3",
            required: bool = False,
            **kwargs
    ):
        """
        :param package: the colcon package name hosting the node
        :param module: the Python module to execute
        :param config: the configuration file to pass to the node
        :param prefix: a set of commands/arguments to precede the cmd, used for
            things like gdb/valgrind and defaults to the LaunchConfiguration
            called 'launch-prefix'. Note that a non-default prefix provided in
            a launch file will override the prefix provided via the `launch-prefix`
            launch configuration regardless of whether the `launch-prefix-filter` launch
            configuration is provided.
        :param name: The label used to represent the process, as a string or a Substitution
            to be resolved at runtime, defaults to the basename of the executable
        :param cwd: The directory in which to run the executable
        :param env: Dictionary of environment variables to be used, starting from a clean
            environment. If None, the current environment of the launch context is used.
        :param additional_env: Dictionary of environment variables to be added. If env was
            None, they are added to the current environment. If not, env is updated with
            additional_env.
        :param arguments: list of extra arguments for the executable
        :param: shell if True, a shell is used to execute the cmd
        :param: sigterm_timeout time until shutdown should escalate to SIGTERM,
            as a string or a list of strings and Substitutions to be resolved
            at runtime, defaults to the LaunchConfiguration called
            'sigterm_timeout'
        :param: sigkill_timeout time until escalating to SIGKILL after SIGTERM,
            as a string or a list of strings and Substitutions to be resolved
            at runtime, defaults to the LaunchConfiguration called
            'sigkill_timeout'
        :param: emulate_tty emulate a tty (terminal), defaults to False, but can
            be overridden with the LaunchConfiguration called 'emulate_tty',
            the value of which is evaluated as true or false according to
            :py:func:`evaluate_condition_expression`.
            Throws :py:exc:`InvalidConditionExpressionError` if the
            'emulate_tty' configuration does not represent a boolean.
        :param: output configuration for process output logging. Defaults to 'log'
            i.e. log both stdout and stderr to launch main log file and stderr to
            the screen.
            Overridden externally by the OVERRIDE_LAUNCH_PROCESS_OUTPUT envvar value.
            See `launch.logging.get_output_loggers()` documentation for further
            reference on all available options.
        :param: output_format for logging each output line, supporting `str.format()`
            substitutions with the following keys in scope: `line` to reference the raw
            output line and `this` to reference this action instance.
        :param: cached_output if `True`, both stdout and stderr will be cached.
            Use get_stdout() and get_stderr() to read the buffered output.
        :param: on_exit list of actions to execute upon process exit.
        :param: respawn if 'True', relaunch the process that abnormally died.
            Either a boolean or a Substitution to be resolved at runtime. Defaults to 'False'.
        :param: respawn_delay a delay time to relaunch the died process if respawn is 'True'.
        :param: respawn_max_retries number of times to respawn the process if respawn is 'True'.
                A negative value will respawn an infinite number of times (default behavior).
        """
        # arguments
        arguments = arguments or []
        # find package
        package: Optional[Package] = Package.from_name(package)
        if package is None:
            raise ValueError(f"Package '{package}' not found")
        # check configuration file
        if config is not None:
            if not package.has_config(config):
                configs: str = "\n\t".join(package.all_configs())
                raise ValueError(f"Configuration file '{config}' not found in package '{package.name}'. "
                                 f"Available configuration files are:\n\t{configs}")
            arguments.extend(["--config", config])
        # required nodes terminate the whole thing when they die
        # TODO: implement this
        # ---
        super().__init__(
            module=module,
            prefix=prefix,
            name=name,
            cwd=cwd,
            env=env,
            additional_env=additional_env,
            arguments=arguments,
            shell=shell,
            sigterm_timeout=sigterm_timeout,
            sigkill_timeout=sigkill_timeout,
            emulate_tty=emulate_tty,
            output=output,
            output_format=output_format,
            cached_output=cached_output,
            log_cmd=True,
            on_exit=on_exit,
            respawn=respawn,
            respawn_delay=respawn_delay,
            respawn_max_retries=respawn_max_retries,
            runtime=runtime,
            **kwargs
        )
