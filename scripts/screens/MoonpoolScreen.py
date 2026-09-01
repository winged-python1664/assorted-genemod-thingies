import random
import itertools
import os

from re import sub
import i18n
import pygame
import pygame_gui
import ujson
from pygame_gui.core import UIContainer

from scripts.config import get_config

from scripts.cat.cats import Cat
from scripts.cat.sprites.display_sprites import update_sprite
from scripts.cat.enums import CatRank, CatGroup, CatStanding, CatAge
from scripts.cat.skills import CatSkills
from scripts.clan import OtherClan
from scripts.game_structure import game
from scripts.clan_package.settings.clan_settings import (
    set_clan_setting,
    get_clan_setting,
)
from scripts.game_structure import constants
from scripts.game_structure.screen_settings import MANAGER
from scripts.ui.elements.sprite_button import UISpriteButton
from scripts.ui.elements.image_button import UIImageButton
from ..ui.elements.checkbox import UICheckbox
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.screens.Screens import Screens
from scripts.ui.generate_box import get_box, BoxStyles
from scripts.ui.generate_button import get_button_dict, ButtonStyles
from scripts.ui.icon import Icon
from scripts.ui.theme import get_text_box_theme
from scripts.events_module.text_adjust import shorten_text_to_fit
from scripts.ui.scale import ui_scale, ui_scale_dimensions
from scripts.ui.elements.text_box_tweaked import UITextBoxTweaked
from scripts.clan_package.get_clan_cats import (
    find_alive_cats_with_rank,
    get_living_clan_cat_count,
)
from scripts.ui.windows.cruel_locked_action import CruelLockedAction


class MoonpoolScreen(Screens):
    def __init__(self, name=None):
        super().__init__(name)

        self.current_page_clan = 1
        self.current_page_sc = 1
        self.help_button = None
        self.back_button = None

        self.focus_tab = None
        self.focus_clan_cat = None
        self.focus_sc_cat = None
        self.temper = None
        self.no_prophet = False
        self.prev_group = []
        self.editing_message = False
        self.user_message = None
        self.user_message_text = None
        self.user_cat_message_text = None
        self.user_age_message_text = None

        self.screen_elements = {}
        self.focus_frame_container = None
        self.focus_frame_elements = {}

        self.cat_selection_elements = {}
        self.text_selection_elements = {}
        self.cat_buttons = {}
        self.clan_cat_buttons = {}
        self.sc_cat_buttons = {}
        self.fav = {}
        self.text_box = {}
        self.focus_cat_container = None
        self.focus_cat_elements = {}
        self.cat_selection_container = None
        self.focus_cat_images = {}
        self.focus_cat_info = {}

        self.checkboxes = {}
        self.message_elements = {}
        self.message_container = None
        self.show_message_elements = {}
        self.edit_message_elements = {}
        self.message_buttons = {}

        self.message_type = None

        if game.selected_clan is not None:
            self.moonthing = game.selected_clan.moonthing

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.back_button:
                self.change_screen(game.last_screen_forupdate)
            elif event.ui_element == self.cat_selection_elements["clan_page_right"]:
                self.current_page_clan += 1
                self.update_cats(group="clan")
            elif event.ui_element == self.cat_selection_elements["clan_page_left"]:
                self.current_page_clan -= 1
                self.update_cats(group="clan")
            elif event.ui_element == self.cat_selection_elements["sc_page_right"]:
                self.current_page_sc += 1
                self.update_cats(group="sc")
            elif event.ui_element == self.cat_selection_elements["sc_page_left"]:
                self.current_page_sc -= 1
                self.update_cats(group="sc")
            elif event.ui_element == self.cat_selection_elements["clans"]:
                self.open_clans_tab()
            elif event.ui_element == self.cat_selection_elements["sc"]:
                if self.editing_message == False:
                    self.open_sc_tab()
            elif event.ui_element == self.cat_selection_elements["text"]:
                if self.focus_clan_cat is not None and self.focus_sc_cat is not None:
                    self.open_text_tab()
                else:
                    return

            elif event.ui_element in self.clan_cat_buttons.values():
                self.focus_clan_cat = event.ui_element.return_cat_object()
                self.update_cat_focus()
            elif event.ui_element in self.sc_cat_buttons.values():
                self.focus_sc_cat = event.ui_element.return_cat_object()
                self.update_cat_focus()
            elif event.ui_element == self.checkboxes["edit_text"]:
                self.editing_message = self.checkboxes["edit_text"].checked
                if self.editing_message == False:
                    self.update_text_focus()
                    self.edit_message_elements["message"].show()
                    self.edit_message_elements["cat"].show()

                    self.show_message_elements["message"].hide()
                    self.show_message_elements["cat"].hide()

                    self.message_buttons["send"].disable()

                    self.cat_selection_elements["clans"].disable()
                    self.cat_selection_elements["sc"].disable()
                else:
                    self.user_message_text = sub(
                        r"[^A-Za-z0-9<->/.()*'&#!?,| _+=@~:;[{}%$^`]]+",
                        "",
                        self.edit_message_elements["message"].get_text(),
                    )
                    self.user_cat_message_text = sub(
                        r"[^A-Za-z0-9<->/.()*'&#!?,| _+=@~:;[{}%$^`]]+",
                        "",
                        self.edit_message_elements["cat"].get_text(),
                    )
                    self.record_user_text()
                    self.update_text_focus()
                    self.edit_message_elements["message"].hide()
                    self.edit_message_elements["cat"].hide()

                    self.show_message_elements["message"].show()
                    self.show_message_elements["cat"].show()

                    self.message_buttons["send"].enable()
                    self.cat_selection_elements["clans"].enable()
                    self.cat_selection_elements["sc"].enable()
                self.checkboxes["edit_text"].toggle()

    def record_user_text(self):
        set_clan_setting(
            "user_message",
            {
                "message_text": self.user_message_text,
                "cat_history_text": self.user_cat_message_text,
            },
        )

    def screen_switches(self):
        super().screen_switches()
        self.hide_menu_buttons()

        self.moonthing = game.selected_clan.moonthing

        # BACK AND HELP
        self.back_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((25, 25), (105, 30))),
            "buttons.back",
            get_button_dict(ButtonStyles.SQUOVAL, (105, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
        )
        self.help_button = UIImageButton(
            ui_scale(pygame.Rect((725, 25), (34, 34))),
            "",
            object_id="#help_button",
            manager=MANAGER,
            tool_tip_text="screens.moonpool.help_tooltip",
        )

        self.no_prophet = False
        if not game.clan.prophet or not game.clan.prophet.status.alive_in_player_clan:
            self.no_prophet = True

        try:
            self.screen_elements["bg_image"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((0, 0), (700, 450))),
                pygame.image.load(
                    f"resources/images/{game.clan.sc_bg}.png"
                ).convert_alpha(),
                object_id="#lead_den_bg",
                starting_height=1,
                manager=MANAGER,
            )
        except FileNotFoundError:
            self.screen_elements["bg_image"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((0, 0), (700, 450))),
                pygame.image.load(
                    f"resources/images/moonpool.png"
                ).convert_alpha(),
                object_id="#lead_den_bg",
                starting_height=1,
                manager=MANAGER,
            )

        self.create_focus_frame()
        self.create_cat_selection_box()
        self.create_text_selection_box()
        self.update_cat_focus()
        self.cat_selection_elements["clan_page_left"].disable()
        self.cat_selection_elements["clan_page_right"].disable()
        self.cat_selection_elements["sc_page_left"].disable()
        self.cat_selection_elements["sc_page_right"].disable()

        self.screen_elements["notice_text"] = pygame_gui.elements.UITextBox(
            relative_rect=ui_scale(pygame.Rect((68, 360), (445, -1))),
            html_text=f"screens.moonpool.notice_text_{self.moonthing}",
            object_id=get_text_box_theme("#text_box_30_horizcenter_spacing_95"),
            manager=MANAGER,
            text_kwargs={
                "m_c": self.focus_clan_cat,
                "r_c": self.focus_sc_cat,
                "count": 1,
            },
        )
        self.screen_elements["temper_text"] = pygame_gui.elements.UITextBox(
            relative_rect=ui_scale(pygame.Rect((68, 395), (445, -1))),
            html_text="screens.moonpool.temper_text",
            object_id=get_text_box_theme("#text_box_30_horizcenter"),
            manager=MANAGER,
            text_kwargs={
                "temper": i18n.t(
                    "screens.moonpool.temper",
                    first_temper=i18n.t(f"screens.moonpool.{game.starclan.temperament[0]}"),
                    second_temper=i18n.t(f"screens.moonpool.{game.starclan.temperament[1]}"),
                ),
            },
            # anchors={"top_target": self.screen_elements["notice_text"]},
        )

        if not get_living_clan_cat_count(Cat):
            self.no_prophet = True
            self.screen_elements["notice_text"].set_text(
                "screens.moonpool.no_cats"
            )
        if self.no_prophet or not game.clan.prophet.status.alive_in_player_clan:
            self.no_prophet = True
            self.screen_elements["notice_text"].set_text(
                "screens.moonpool.no_prophet"
            )
        elif game.clan.prophet.not_working():
            self.no_prophet = True
            self.screen_elements["notice_text"].set_text(
                "screens.moonpool.prophet_sick",
                text_kwargs={"m_c": game.clan.prophet},
            )

        if get_clan_setting("moonpool_message"):
            self.focus_clan_cat = Cat.fetch_cat(get_clan_setting("moonpool_message")["clan_cat_ID"])
            self.focus_sc_cat = Cat.fetch_cat(get_clan_setting("moonpool_message")["sc_cat_ID"])
            self.update_cat_focus()
        else:
            self.focus_clan_cat = None
            self.focus_sc_cat = None
            self.update_cat_focus()

    def exit_screen(self):
        self.back_button.kill()
        self.help_button.kill()

        for ele in self.screen_elements:
            self.screen_elements[ele].kill()

        self.focus_frame_container.kill()
        self.cat_selection_container.kill()
        self.text_selection_container.kill()
        self.message_container.kill()

        self.current_page_clan = 1
        self.current_page_sc = 1

    def create_focus_frame(self):
        self.focus_frame_container = UIContainer(
            ui_scale(pygame.Rect((509, 65), (240, 398))),
            object_id="#focus_frame_container",
            starting_height=3,
            manager=MANAGER,
        )
        self.focus_frame_elements["frame"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((0, 0), (240, 364))),
            get_box(BoxStyles.ROUNDED_BOX, (240, 364)),
            container=self.focus_frame_container,
            starting_height=1,
            manager=MANAGER,
        )

    def update_cat_focus(self):
        if self.focus_cat_container:
            self.focus_cat_container.kill()

        self.focus_cat_container = UIContainer(
            ui_scale(pygame.Rect((0, 0), (240, 398))),
            object_id="#focus_cat_container",
            container=self.focus_frame_container,
            starting_height=1,
            manager=MANAGER,
        )

        if self.focus_clan_cat is not None:
            self.focus_cat_elements["clan_cat_sprite"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((0, 8), (100, 100))),
                pygame.transform.scale(
                    self.focus_clan_cat.sprite, ui_scale_dimensions((100, 100))
                ),
                object_id="#clan_cat_sprite",
                container=self.focus_cat_container,
                starting_height=1,
                manager=MANAGER,
                anchors={"centerx": "centerx"},
            )
            self.focus_cat_elements["clan_cat_name"] = pygame_gui.elements.UILabel(
                ui_scale(pygame.Rect((0, 1), (215, -1))),
                text=shorten_text_to_fit(str(self.focus_clan_cat.name), 220, 15),
                object_id="#text_box_30_horizcenter",
                container=self.focus_cat_container,
                manager=MANAGER,
                anchors={
                    "centerx": "centerx",
                    "top_target": self.focus_cat_elements["clan_cat_sprite"],
                },
            )
            self.focus_cat_elements["clan_cat_status"] = pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((0, 1), (218, -1))),
                text=f"general.{self.focus_clan_cat.status.rank}",
                object_id="#text_box_22_horizcenter",
                container=self.focus_cat_container,
                manager=MANAGER,
                anchors={
                    "centerx": "centerx",
                    "top_target": self.focus_cat_elements["clan_cat_name"],
                },
                text_kwargs={"count": 1},
            )
            self.focus_cat_elements["clan_cat_skills"] = pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((0, 1), (218, -1))),
                text="screens.moonpool.cat_skill",
                object_id="#text_box_22_horizcenter",
                container=self.focus_cat_container,
                manager=MANAGER,
                anchors={
                    "centerx": "centerx",
                    "top_target": self.focus_cat_elements["clan_cat_status"],
                },
                text_kwargs={"skill": self.focus_clan_cat.skills.skill_string(short=True)},
            )
            clan_cat_pronouns = (
                self.focus_clan_cat.pronouns[0].get("subject") + "/" + self.focus_clan_cat.pronouns[0].get("object")
            )
            self.focus_cat_elements["clan_cat_pronouns"] = pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((0, 1), (218, -1))),
                text=clan_cat_pronouns,
                object_id="#text_box_22_horizcenter",
                container=self.focus_cat_container,
                manager=MANAGER,
                anchors={
                    "centerx": "centerx",
                    "top_target": self.focus_cat_elements["clan_cat_skills"],
                },
                text_kwargs={"count": 1},
            )

        if self.focus_sc_cat is not None:
            self.focus_cat_elements["sc_cat_sprite"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((0, 178), (100, 100))),
                pygame.transform.scale(
                    self.focus_sc_cat.sprite, ui_scale_dimensions((100, 100))
                ),
                object_id="#sc_cat_sprite",
                container=self.focus_cat_container,
                starting_height=1,
                manager=MANAGER,
                anchors={"centerx": "centerx"},
            )
            self.focus_cat_elements["sc_cat_name"] = pygame_gui.elements.UILabel(
                ui_scale(pygame.Rect((0, 1), (215, -1))),
                text=shorten_text_to_fit(str(self.focus_sc_cat.name), 220, 15),
                object_id="#text_box_30_horizcenter",
                container=self.focus_cat_container,
                manager=MANAGER,
                anchors={
                    "centerx": "centerx",
                    "top_target": self.focus_cat_elements["sc_cat_sprite"],
                },
            )
            self.focus_cat_elements["sc_cat_status"] = pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((0, 1), (218, -1))),
                text=f"general.{self.focus_sc_cat.status.rank}",
                object_id="#text_box_22_horizcenter",
                container=self.focus_cat_container,
                manager=MANAGER,
                anchors={
                    "centerx": "centerx",
                    "top_target": self.focus_cat_elements["sc_cat_name"],
                },
                text_kwargs={"count": 1},
            )
            self.focus_cat_elements["sc_cat_skills"] = pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((0, 1), (218, -1))),
                text="screens.moonpool.cat_skill",
                object_id="#text_box_22_horizcenter",
                container=self.focus_cat_container,
                manager=MANAGER,
                anchors={
                    "centerx": "centerx",
                    "top_target": self.focus_cat_elements["sc_cat_status"],
                },
                text_kwargs={"skill": self.focus_sc_cat.skills.skill_string(short=True)},
            )
            sc_cat_pronouns = (
                self.focus_sc_cat.pronouns[0].get("subject") + "/" + self.focus_sc_cat.pronouns[0].get("object")
            )
            self.focus_cat_elements["sc_cat_pronouns"] = pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((0, 1), (218, -1))),
                text=sc_cat_pronouns,
                object_id="#text_box_22_horizcenter",
                container=self.focus_cat_container,
                manager=MANAGER,
                anchors={
                    "centerx": "centerx",
                    "top_target": self.focus_cat_elements["sc_cat_skills"],
                },
                text_kwargs={"count": 1},
            )

    def create_cat_selection_box(self):
        self.cat_selection_container = pygame_gui.elements.UIAutoResizingContainer(
            ui_scale(pygame.Rect((59, 455), (0, 0))),
            object_id="#cat_selection_container",
            starting_height=1,
            manager=MANAGER,
        )
        self.cat_selection_elements["clan_page_left"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 70), (34, 34))),
            Icon.ARROW_LEFT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            container=self.cat_selection_container,
            starting_height=1,
            manager=MANAGER,
        )
        self.cat_selection_elements["clan_page_right"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((646, 70), (34, 34))),
            Icon.ARROW_RIGHT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            container=self.cat_selection_container,
            starting_height=1,
            manager=MANAGER,
        )

        self.cat_selection_elements["sc_page_left"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 70), (34, 34))),
            Icon.ARROW_LEFT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            container=self.cat_selection_container,
            starting_height=1,
            manager=MANAGER,
        )
        self.cat_selection_elements["sc_page_left"].hide()
        self.cat_selection_elements["sc_page_right"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((646, 70), (34, 34))),
            Icon.ARROW_RIGHT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            container=self.cat_selection_container,
            starting_height=1,
            manager=MANAGER,
        )
        self.cat_selection_elements["sc_page_right"].hide()

        self.cat_selection_elements["frame"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((28, 0), (624, 174))),
            get_box(BoxStyles.ROUNDED_BOX, (624, 174)),
            container=self.cat_selection_container,
            starting_height=2,
            manager=MANAGER,
        )

        self.cat_selection_elements["clans"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((45, -30), (50, 34))),
            "screens.moonpool.clans_tab",
            get_button_dict(ButtonStyles.HORIZONTAL_TAB, (50, 34)),
            object_id="@buttonstyles_horizontal_tab",
            container=self.cat_selection_container,
            starting_height=1,
            manager=MANAGER,
        )

        self.cat_selection_elements["sc"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((20, -30), (75, 34))),
            "screens.moonpool.sc_tab",
            get_button_dict(ButtonStyles.HORIZONTAL_TAB, (75, 34)),
            object_id="@buttonstyles_horizontal_tab",
            container=self.cat_selection_container,
            starting_height=1,
            manager=MANAGER,
            anchors={"left": "left", "left_target": self.cat_selection_elements["clans"]},
        )

        self.cat_selection_elements["text"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((20, -30), (50, 34))),
            "screens.moonpool.text_tab",
            get_button_dict(ButtonStyles.HORIZONTAL_TAB, (50, 34)),
            object_id="@buttonstyles_horizontal_tab",
            container=self.cat_selection_container,
            starting_height=1,
            manager=MANAGER,
            anchors={"left": "left", "left_target": self.cat_selection_elements["sc"]},
        )

        self.cat_list_container = pygame_gui.elements.UIAutoResizingContainer(
            ui_scale(pygame.Rect((40, 47), (0, 0))),
            container=self.cat_selection_container,
            starting_height=3,
            object_id="#cat_list_container",
            manager=MANAGER,
        )

        self.clan_cat_list_container = pygame_gui.elements.UIAutoResizingContainer(
            ui_scale(pygame.Rect((40, 47), (0, 0))),
            container=self.cat_list_container,
            starting_height=3,
            object_id="#clan_cat_list_container",
            manager=MANAGER,
        )

        self.sc_cat_list_container = pygame_gui.elements.UIAutoResizingContainer(
            ui_scale(pygame.Rect((40, 47), (0, 0))),
            container=self.cat_list_container,
            starting_height=3,
            object_id="#sc_cat_list_container",
            manager=MANAGER,
        )

    def create_text_selection_box(self):
        self.text_selection_container = pygame_gui.elements.UIAutoResizingContainer(
            ui_scale(pygame.Rect((59, 455), (0, 0))),
            object_id="#text_selection_container",
            starting_height=1,
            manager=MANAGER,
            visible=False,
        )
        self.text_selection_elements["frame"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((28, 0), (624, 174))),
            get_box(BoxStyles.ROUNDED_BOX, (624, 174)),
            container=self.text_selection_container,
            starting_height=2,
            manager=MANAGER,
        )

        self.message_container = pygame_gui.elements.UIAutoResizingContainer(
            ui_scale(pygame.Rect((70, 21), (0, 0))),
            object_id="#edit_message_container",
            container=self.text_selection_container,
            starting_height=1,
            manager=MANAGER,
        )

    def update_text_focus(self):
        self.message_elements["frame_mess"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((0, 0), (285, 130))),
            get_box(BoxStyles.ROUNDED_BOX, (285, 130)),
            container=self.message_container,
            manager=MANAGER,
        )
        self.message_elements["frame_cat"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((8, 0), (260, 130))),
            get_box(BoxStyles.ROUNDED_BOX, (260, 130)),
            container=self.message_container,
            manager=MANAGER,
            anchors={"left": "left", "left_target": self.message_elements["frame_mess"]}
        )

        self.edit_message_elements["message"] = pygame_gui.elements.UITextEntryBox(
            ui_scale(pygame.Rect((6, 3), (279, 120))),
            initial_text="screens.moonpool.message_text" if self.user_message_text is None else self.user_message_text,
            object_id="#text_box_26_horizleft_pad_10_14",
            container=self.message_container,
            manager=MANAGER,
            visible=False,
        )
        self.edit_message_elements["cat"] = pygame_gui.elements.UITextEntryBox(
            ui_scale(pygame.Rect((15, 3), (250, 120))),
            initial_text="screens.moonpool.cat_message_text" if self.user_cat_message_text is None else self.user_cat_message_text,
            object_id="#text_box_26_horizleft_pad_10_14",
            container=self.message_container,
            manager=MANAGER,
            anchors={"left": "left", "left_target": self.edit_message_elements["message"]},
            visible=False,
        )

        self.show_message_elements["message"] = UITextBoxTweaked(
            "screens.moonpool.message_text" if self.user_message_text is None else self.user_message_text,
            ui_scale(pygame.Rect((6, 3), (279, 124))),
            object_id="#text_box_26_horizleft_pad_10_14",
            line_spacing=1,
            container=self.message_container,
            manager=MANAGER,
        )
        self.show_message_elements["cat"] = UITextBoxTweaked(
            "screens.moonpool.cat_message_text" if self.user_cat_message_text is None else self.user_cat_message_text,
            ui_scale(pygame.Rect((15, 3), (250, 124))),
            object_id="#text_box_26_horizleft_pad_10_14",
            line_spacing=1,
            container=self.message_container,
            manager=MANAGER,
            anchors={"left": "left", "left_target": self.show_message_elements["message"]},
        )

        self.checkboxes["edit_text"] = UICheckbox(
            position=(38, 35),
            manager=MANAGER,
            container=self.text_selection_container,
            starting_height=2,
            check=self.editing_message,
            tool_tip_text="screens.moonpool.save_message"
        )

        self.message_buttons["send"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((38, 15), (60, 30))),
            "screens.moonpool.send_message",
            get_button_dict(ButtonStyles.SQUOVAL, (60, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            container=self.text_selection_container,
            anchors={"top_target": self.checkboxes["edit_text"]},
        )

    def open_clans_tab(self):
        self.cat_selection_container.show()
        self.text_selection_container.hide()
        self.cat_selection_elements["clan_page_left"].show()
        self.cat_selection_elements["clan_page_right"].show()
        self.cat_selection_elements["sc_page_left"].hide()
        self.cat_selection_elements["sc_page_right"].hide()

        self.cat_selection_elements["clans"].disable()
        self.cat_selection_elements["sc"].enable()
        if self.focus_clan_cat is not None and self.focus_sc_cat is not None:
            self.cat_selection_elements["text"].enable()

        self.update_cats(group="clan")

    def open_sc_tab(self):
        self.cat_selection_container.show()
        self.text_selection_container.hide()
        self.cat_selection_elements["clan_page_left"].hide()
        self.cat_selection_elements["clan_page_right"].hide()
        self.cat_selection_elements["sc_page_left"].show()
        self.cat_selection_elements["sc_page_right"].show()

        self.cat_selection_elements["clans"].enable()
        self.cat_selection_elements["sc"].disable()
        if self.focus_clan_cat is not None and self.focus_sc_cat is not None:
            self.cat_selection_elements["text"].enable()

        self.update_cats(group="sc")

    def open_text_tab(self):
        self.cat_selection_container.hide()
        self.text_selection_container.show()
        self.cat_selection_elements["clans"].show()
        self.cat_selection_elements["sc"].show()
        self.cat_selection_elements["text"].show()

        self.cat_selection_elements["clans"].enable()
        self.cat_selection_elements["sc"].enable()
        self.cat_selection_elements["text"].disable()
        self.update_text_focus()

    def update_cats(self, group):
        """
        handles finding and displaying cats
        """
        clan_cats = [
            i
            for i in Cat.all_cats.values()
            if not i.dead
            and i.status.group == CatGroup.PLAYER_CLAN
        ]
        sc_cats = [
            i
            for i in Cat.all_cats.values()
            if i.dead
            and i.status.group == CatGroup.STARCLAN
        ]

        # separate them into chunks for the pages
        clan_cat_chunks = self.get_list_chunks(clan_cats, 20)
        sc_cat_chunks = self.get_list_chunks(sc_cats, 20)

        Cat.sort_cats(clan_cats)
        Cat.sort_cats(sc_cats)

        if group == "clan":
            self.prev_group == "clan"
        elif group == "sc":
            all_instructors = [game.clan.instructor] + [clan.instructor for clan in game.clan.all_other_clans if clan.instructor]
            for ins in all_instructors[::-1]:
                if (
                    ins.status.group == CatGroup.STARCLAN
                ):
                    if ins in sc_cats:
                        sc_cats.remove(ins)
                        sc_cats.insert(0, ins)

            self.prev_group == "sc"
        else:
            self.prev_group == "clan"

        # clamp current page to a valid page number
        if group == "clan":
            self.current_page_clan = max(1, min(self.current_page_clan, len(clan_cat_chunks)))
        if group == "sc":
            self.current_page_sc = max(1, min(self.current_page_sc, len(sc_cat_chunks)))

        # handles which arrow buttons are clickable
        if group == "clan":
            if len(clan_cat_chunks) <= 1:
                self.cat_selection_elements["clan_page_left"].disable()
                self.cat_selection_elements["clan_page_right"].disable()
            elif self.current_page_clan >= len(clan_cat_chunks):
                self.cat_selection_elements["clan_page_left"].enable()
                self.cat_selection_elements["clan_page_right"].disable()
            elif self.current_page_clan == 1 and len(clan_cat_chunks) > 1:
                self.cat_selection_elements["clan_page_left"].disable()
                self.cat_selection_elements["clan_page_right"].enable()
            else:
                self.cat_selection_elements["clan_page_left"].enable()
                self.cat_selection_elements["clan_page_right"].enable()

        if group == "sc":
            if len(sc_cat_chunks) <= 1:
                self.cat_selection_elements["sc_page_left"].disable()
                self.cat_selection_elements["sc_page_right"].disable()
            elif self.current_page_sc >= len(sc_cat_chunks):
                self.cat_selection_elements["sc_page_left"].enable()
                self.cat_selection_elements["sc_page_right"].disable()
            elif self.current_page_sc == 1 and len(sc_cat_chunks) > 1:
                self.cat_selection_elements["sc_page_left"].disable()
                self.cat_selection_elements["sc_page_right"].enable()
            else:
                self.cat_selection_elements["sc_page_left"].enable()
                self.cat_selection_elements["sc_page_right"].enable()

        # CREATE DISPLAY
        display_cats = []
        for marker in self.fav:
            self.fav[marker].kill()
        self.fav = {}
        if group == "clan":
            if clan_cat_chunks:
                display_cats = clan_cat_chunks[self.current_page_clan - 1]
        if group == "sc":
            if sc_cat_chunks:
                display_cats = sc_cat_chunks[self.current_page_sc - 1]

        # Kill all currently displayed cats
        for ele in self.cat_buttons:
            self.cat_buttons[ele].kill()
        self.cat_buttons = {}

        pos_x = 0
        pos_y = 0
        i = 0

        for cat in display_cats:
            if not cat.sprite:
                update_sprite(cat)
            if get_clan_setting("show fav") and cat.favourite:
                self.fav[str(i)] = pygame_gui.elements.UIImage(
                    ui_scale(pygame.Rect((5+ pos_x, pos_y), (50, 50))),
                    pygame.transform.scale(
                        pygame.image.load(
                            f"resources/images/fav_marker{cat.favourite}.png"
                        ).convert_alpha(),
                        ui_scale_dimensions((50, 50)),
                    ),
                    container=self.cat_list_container,
                )
                self.fav[str(i)].disable()
            self.cat_buttons[f"sprite{str(i)}"] = UISpriteButton(
                ui_scale(pygame.Rect((5 + pos_x, pos_y), (50, 50))),
                cat.sprite,
                cat_object=cat,
                container=self.cat_list_container,
                object_id=f"#sprite{str(i)}",
                tool_tip_text=str(cat.name),
                starting_height=2,
                manager=MANAGER,
            )

            if group == "sc":
                self.sc_cat_buttons = self.cat_buttons
            else:
                self.clan_cat_buttons = self.cat_buttons

            pos_x += 60
            if pos_x >= 590:
                pos_x = 0
                pos_y += 60

            i += 1

    def handle_message(self):
        set_clan_setting("moonpool_event", True)
        user_message = self.user_message_text
        user_cat_message = self.user_cat_message_text

        set_clan_setting(
            "moonpool_message",
            {
                "clan_cat_ID": self.focus_clan_cat.ID,
                "sc_cat_ID": self.focus_sc_cat.ID,
                "message_text": user_message,
                "cat_history": user_cat_message,
            }
        )
