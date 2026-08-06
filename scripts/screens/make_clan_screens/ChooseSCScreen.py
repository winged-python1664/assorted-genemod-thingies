import i18n
import pygame
import pygame_gui
from pygame_gui.core import UIContainer

from scripts.game_structure import constants
from scripts.game_structure.screen_settings import MANAGER
from scripts.screens.enums import GameScreen
from scripts.ui.elements.image_button import UIImageButton
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.ui.generate_box import BoxStyles, get_box
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.ui.icon import Icon
from scripts.ui.scale import ui_scale, ui_scale_dimensions, ui_scale_offset


from scripts.screens.make_clan_screens.MakeClanScreenBase import MakeClanScreenBase
from scripts.ui.windows.cruel_locked_action import CruelLockedAction


class ChooseSCScreen(MakeClanScreenBase):
    def __init__(self, name="choose_camp_screen"):
        super().__init__(name)
        self.tabs = {}
        self.selected_camp_tab = "classic"
        self.selected_moon_tab = None
        self.layout = None

    def screen_switches(self):
        super().screen_switches()

        # return step buttons to their default position
        self.elements["previous_step"].set_relative_position(
            ui_scale_dimensions((253, 620))
        )
        self.elements["next_step"].set_relative_position(ui_scale_dimensions((0, 620)))
        self.elements["next_step"].disable()

        self.elements["sc_container"] = UIContainer(
            ui_scale(pygame.Rect(((0, 100), (500, 100)))),
            manager=MANAGER,
            anchors={"centerx": "centerx"},
        )

        # Camp Art Choosing Tabs, Dummy buttons, will be overridden.
        self.tabs["classic"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))),
            "",
            visible=False,
            manager=MANAGER,
        )
        self.tabs["nest"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))),
            "",
            visible=False,
            manager=MANAGER,
        )

        self.elements["moon_container"] = UIContainer(
            ui_scale(pygame.Rect((625, 225), (39, 400))),
            manager=MANAGER,
        )

        self.tabs["pool_tab"] = UIImageButton(
            ui_scale(pygame.Rect((-3, 30), (39, 34))),
            "",
            object_id="#moonpool_button",
            container=self.elements["moon_container"],
            manager=MANAGER,
        )
        self.tabs["stone_tab"] = UIImageButton(
            ui_scale(pygame.Rect((-3, 30), (39, 34))),
            "",
            object_id="#moonstone_button",
            container=self.elements["moon_container"],
            manager=MANAGER,
            anchors={"top_target": self.tabs["pool_tab"]}
        )

        self.pool_image = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))),
            "",
            visible=False,
            manager=MANAGER,
        )
        self.stone_image = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))),
            "",
            visible=False,
            manager=MANAGER,
        )

        # art frame
        self.draw_art_frame()
        self.refresh_selected_camp()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.elements["previous_step"]:
                self.set_bg(None)
                self.change_screen(GameScreen.MAKE_CLAN_CHOOSE_CAMP)
            elif event.ui_element == self.tabs["classic"]:
                self.selected_camp_tab = "classic"
                self.refresh_selected_camp()
            elif event.ui_element == self.tabs["nest"]:
                self.selected_camp_tab = "nest"
                self.refresh_selected_camp()
            elif event.ui_element == self.tabs["pool_tab"]:
                self.selected_moon_tab = "pool"
                self.refresh_selected_camp()
            elif event.ui_element == self.tabs["stone_tab"]:
                self.selected_moon_tab = "stone"
                self.refresh_selected_camp()
            elif event.ui_element == self.elements["next_step"]:
                self.clan_info.sc_bg = f"{self.selected_camp_tab}"
                self.change_screen(GameScreen.MAKE_CLAN_CHOOSE_SYMBOL)

        return super().handle_event(event)

    def exit_screen(self):
        for ele in self.tabs.values():
            ele.kill()
        self.pool_image.kill()
        self.stone_image.kill()

        super().exit_screen()

    def draw_art_frame(self):
        if "art_frame" in self.elements:
            return
        self.elements["art_frame"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect(((0, 10), (466, 416)))),
            get_box(BoxStyles.FRAME, (466, 416)),
            manager=MANAGER,
            starting_height=2,
            anchors={"center": "center"},
        )

    def refresh_selected_camp(self):
        """Updates selected camp image and tabs"""
        self.tabs["classic"].kill()
        self.tabs["nest"].kill()
        self.pool_image.kill()
        self.stone_image.kill()

        if self.clan_info.sc_bg and self.selected_camp_tab and self.selected_moon_tab is not None:
            self.elements["next_step"].enable()

        if self.selected_camp_tab in constants.LAYOUTS:
            self.layout = constants.LAYOUTS[self.selected_camp_tab]
        else:
            self.layout = constants.LAYOUTS["default"]
            print("layout not found in placements.json")

        self.pool_image = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect(self.layout["pool"], (160, 92))),
            pygame.image.load(
                f"resources/images/camp_bg/sc/moonthing/pool.png"
            ).convert_alpha(),
            object_id="#moonpool",
            starting_height=3,
            visible=False,
        )
        self.stone_image = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect(self.layout["stone"], (102, 106))),
            pygame.image.load(
                "resources/images/camp_bg/sc/moonthing/stone.png"
            ).convert_alpha(),
            object_id="#moonstone",
            starting_height=3,
            manager=MANAGER,
            visible=False,
        )

        if self.selected_moon_tab == "pool":
            self.pool_image.show()
        if self.selected_moon_tab == "stone":
            self.stone_image.show()

        tab_rect = ui_scale(pygame.Rect((0, 0), (85, 30)))
        tab_rect.topright = ui_scale_offset((5, 200))
        self.tabs["classic"] = UISurfaceImageButton(
            tab_rect,
            "screens.make_clan.sc_classic",
            get_button_dict(ButtonStyles.VERTICAL_TAB, (85, 30)),
            object_id="@buttonstyles_vertical_tab",
            manager=MANAGER,
            anchors={"right": "right", "right_target": self.elements["art_frame"]},
        )
        tab_rect = ui_scale(pygame.Rect((0, 0), (95, 30)))
        tab_rect.topright = ui_scale_offset((5, 15))
        self.tabs["nest"] = UISurfaceImageButton(
            tab_rect,
            "screens.make_clan.sc_nest",
            get_button_dict(ButtonStyles.VERTICAL_TAB, (95, 30)),
            object_id="@buttonstyles_vertical_tab",
            manager=MANAGER,
            anchors={
                "right": "right",
                "right_target": self.elements["art_frame"],
                "top_target": self.tabs["classic"],
            },
        )

        self.tabs["classic"].enable()
        self.tabs["nest"].enable()
        if self.selected_camp_tab:
            self.tabs[f"{self.selected_camp_tab}"].disable()

        self.tabs["pool_tab"].enable()
        self.tabs["stone_tab"].enable()
        if self.selected_moon_tab:
            self.tabs[f"{self.selected_moon_tab}_tab"].disable()

        # I have to do this for proper layering.
        if "camp_art" in self.elements:
            self.elements["camp_art"].kill()
        if self.clan_info.sc_bg:
            src = pygame.image.load(
                self.get_sc_art_path(self.selected_camp_tab)
            ).convert_alpha()
            self.elements["camp_art"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((175, 160), (450, 400))),
                pygame.transform.scale(
                    src.copy(),
                    ui_scale_dimensions((450, 400)),
                ),
                manager=MANAGER,
            )
            self.get_camp_bg(src)

        self.draw_art_frame()
