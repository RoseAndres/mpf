"""Handles all light updates."""
import asyncio
from typing import Dict

from mpf.core.machine import MachineController
from mpf.core.settings_controller import SettingEntry

from mpf.core.rgb_color import RGBColorCorrectionProfile, RGBColor

from mpf.core.mpf_controller import MpfController


class LightController(MpfController):

    """Handles light updates and light monitoring."""

    def __init__(self, machine: MachineController) -> None:
        """Initialise lights controller."""
        super().__init__(machine)

        # Generate and add color correction profiles to the machine
        self.light_color_correction_profiles = dict()       # type: Dict[str, RGBColorCorrectionProfile]

        # will only get initialised if there are lights
        self._initialised = False

        self._monitor_update_task = None                    # type: asyncio.Task

        if 'named_colors' in self.machine.config:
            self._load_named_colors()

    def _load_named_colors(self):
        """Load named colors from config."""
        for name, color in self.machine.config['named_colors'].items():
            RGBColor.add_color(name, color)

    def initialise_light_subsystem(self):
        """Initialise the light subsystem."""
        if self._initialised:
            return
        self._initialised = True
        self.machine.validate_machine_config_section('light_settings')

        if self.machine.config['light_settings']['color_correction_profiles'] is None:
            self.machine.config['light_settings']['color_correction_profiles'] = (
                dict())

        # Create the default color correction profile and add it to the machine
        default_profile = RGBColorCorrectionProfile.default()
        self.light_color_correction_profiles['default'] = default_profile

        # Add any user-defined profiles specified in the machine config file
        for profile_name, profile_parameters in (
                self.machine.config['light_settings']
                ['color_correction_profiles'].items()):
            self.machine.config_validator.validate_config(
                'color_correction_profile',
                self.machine.config['light_settings']['color_correction_profiles']
                [profile_name], profile_parameters)

            profile = RGBColorCorrectionProfile(profile_name)
            profile.generate_from_parameters(
                gamma=profile_parameters['gamma'],
                whitepoint=profile_parameters['whitepoint'],
                linear_slope=profile_parameters['linear_slope'],
                linear_cutoff=profile_parameters['linear_cutoff'])
            self.light_color_correction_profiles[profile_name] = profile

        # add setting for brightness
        self.machine.settings.add_setting(SettingEntry("brightness", "Brightness", 100, "brightness", 1.0,
                                                       {0.25: "25%", 0.5: "50%", 0.75: "75%", 1.0: "100% (default)"}))

    def monitor_lights(self):
        """Update the color of lights for the monitor."""
        if not self._monitor_update_task:
            self._monitor_update_task = self.machine.clock.loop.create_task(self._monitor_update_lights())
            self._monitor_update_task.add_done_callback(self._done)

    def _done(self, future: asyncio.Future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def _monitor_update_lights(self):
        colors = {}
        while True:
            for light in self.machine.lights:
                color = light.get_color()
                old = colors.get(light, None)
                if old != color:
                    self.machine.device_manager.notify_device_changes(light, "color", old, color)
                    colors[light] = color
            yield from asyncio.sleep(1 / 30, loop=self.machine.clock.loop)
