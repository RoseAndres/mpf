"""Base class used for things that "play" from the config files, such as
WidgetPlayer, SlidePlayer, etc."""


class ConfigPlayer(object):
    config_file_section = None
    show_section = None
    machine_collection_name = None

    show_players = dict()
    config_file_players = dict()

    def __init__(self, machine):
        self.machine = machine
        self.valid_keys = list()
        self.caller_target_map = dict()
        '''Dict of callers which called this config player. Will be used with
        a clear method. Different config players can use this for different
        things. See the LedPlayer for an example.'''

        try:
            self.process_config(
                    self.machine.machine_config[self.config_file_section])
            self.register_player_events(
                    self.machine.machine_config[self.config_file_section])
        except KeyError:
            pass

        self.machine.mode_controller.register_load_method(
                self.process_config, self.config_file_section)

        self.machine.mode_controller.register_start_method(
                self.register_player_events, self.config_file_section)

        ConfigPlayer.show_players[self.show_section] = self
        ConfigPlayer.config_file_players[self.config_file_section] = self

        self.machine.events.add_handler('init_phase_2', self._initialize)



    def _initialize(self):
        if self.machine_collection_name:
            self.device_collection = getattr(self.machine,
                                             self.machine_collection_name)
        else:
            self.device_collection = None

        try:  # todo remove this when confic spec is filled out
            self.valid_keys = (self.machine.config_validator.config_spec
                               [self.config_file_section].keys())
            # todo move to common validation section
            self.valid_keys.extend(('time', 'key', 'priority'))
        except AttributeError:
            self.valid_keys = list()

    def validate_config(self, config):
        # called first, before config file is cached. Not called if config file
        # is read from cache
        return config

    def validate_show_config(self, config):
        # override if you need a different show processor from config file
        # processor
        return self.validate_config(config)

    def process_config(self, config, **kwargs):
        # called every time mpf starts, regardless of whether config was built
        # from cache or config files
        del kwargs

        # config is localized

        for event, settings in config.items():

            if isinstance(settings, dict):
                settings = [settings]

            final_settings = list()
            for these_settings in settings:

                s = self.machine.config_validator.validate_config(
                        self.config_file_section, these_settings)
                s = self.additional_processing(s)

                final_settings.append(s)

            config[event] = final_settings

    def process_show_config(self, config, **kwargs):
        # override if you need a different show processor from config file
        # processor

        return self.process_config(config, **kwargs)

    def register_player_events(self, config, mode=None, priority=0):
        # config is localized
        del priority

        key_list = list()

        for event, settings in config.items():
            key_list.append(self.machine.events.add_handler(
                    event,
                    self.play,
                    mode=mode,
                    settings=settings))

        return self.unload_player_events, key_list

    def unload_player_events(self, key_list):
        self.machine.events.remove_handlers_by_keys(key_list)

    def additional_processing(self, config):
        return config

    def play(self, settings, mode=None, caller=None, **kwargs):
        # Be sure to include **kwargs in your subclass since events could come
        # in with any parameters
        del settings
        del kwargs

        if caller and caller not in self.caller_target_map:
            self.caller_target_map[caller] = set()

        if mode and not mode.active:
            return  # pragma: no cover

    def clear(self, caller, priority):
        pass