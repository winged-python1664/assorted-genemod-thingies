from random import choice

import pygame
import pygame_gui
from pygame_gui.core import UIContainer

from scripts.cat.cats import create_example_cats
from scripts.config import get_config
from scripts.game_structure.game import switch_get_value, Switch, game_setting_get
from scripts.game_structure.game.switches import switch_set_value
from scripts.game_structure.screen_settings import MANAGER
from scripts.screens.enums import GameScreen
from scripts.screens.make_clan_screens.MakeClanScreenBase import MakeClanScreenBase
from scripts.ui.elements.modified_image import UIModifiedImage
from scripts.ui.elements.image_button import UIImageButton
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.ui.elements.text_box_tweaked import UITextBoxTweaked
from scripts.ui.generate_box import get_box, BoxStyles
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.ui.icon import Icon
from scripts.ui.scale import ui_scale, ui_scale_dimensions
from scripts.ui.theme import get_text_box_theme


class ChooseCodeScreen(MakeClanScreenBase):
    def __init__(self, name="choose_code_screen"):
        super().__init__(name)

        self.code_elements = {}

        self.shown_codes = []
        self.hidden_codes = []
        self.selected_codes = []
        self.first_code = None
        self.top_shown_code = None
        self.last_shown_code = None
        self.final_code = None

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            # PREV/NEXT
            if event.ui_element == self.elements["next_step"]:
                self.change_screen(GameScreen.MAKE_CLAN_CHOOSE_NAME)
            elif event.ui_element == self.elements["previous_step"]:
                if self.clan_info.game_mode == "cruel_season":
                    self.change_screen(GameScreen.MAKE_CLAN_CHOOSE_CARDS)
                else:
                    self.change_screen(GameScreen.MAKE_CLAN_CHOOSE_MODE)

            # CYCLE CODES
            elif event.ui_element == self.elements["page_down"]:
                self.rotate_codes(up=False)
            elif event.ui_element == self.elements["page_up"]:
                self.rotate_codes(up=True)

            elif event.ui_element in self.code_elements.values():
                print("gotta figure out how to get this to work")

                """
            # CHOOSE CODES
            elif event.ui_element in self.code_elements.values():
                code_name = event.code_name
                self.selected_codes.append(code_name)
                self.clan_info.code_rules.append(code_name)
                self.update_codes()
                self.add_chosen_code()
            """

            # UNDO CHOICES
            # elif event.ui_element in self.code_icon_elements.values():
                # self.selected_codes.remove(event.code_name)
                # self.clan_info.code_rules.remove(event.code_name)

        """
        elif event.type == pygame_gui.UI_BUTTON_ON_HOVERED:
            # UPDATE CARD INFO DISPLAY
            if event.ui_element in self.code_elements.values():
                self.update_card_info(event.card_name)
            elif event.ui_element in self.code_icon_elements.values():
                self.update_card_info(event.card_name)
        """

        super().handle_event(event)

    def screen_switches(self):
        super().screen_switches()

        self.elements["header"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((0, 60), (262, 30))),
            pygame.transform.scale(
                pygame.image.load(
                    f"resources/images/wc_{'dark' if game_setting_get('dark mode') else 'light'}.png"
                ).convert_alpha(),
                ui_scale_dimensions((262, 30)),
            ),
            anchors={"centerx": "centerx"},
        )

        # CARD DISPLAY
        self.elements["code_container"] = UIContainer(
            ui_scale(pygame.Rect((12, 95), (584, 570))),
            object_id="#code_container",
            anchors={"centerx": "centerx"},
            manager=MANAGER,
        )

        self.elements["frame"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((2, 5), (580, 380))),
            get_box(BoxStyles.ROUNDED_BOX, (580, 380)),
            container=self.elements["code_container"],
            starting_height=1,
            manager=MANAGER,
        )

        self.elements["info_box"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((-95, 5), (380, 110))),
            get_box(BoxStyles.FRAME, (380, 110)),
            container=self.elements["code_container"],
            manager=MANAGER,
            anchors={
                "centerx": "centerx",
                "top_target": self.elements["frame"],
            },
            starting_height=-1,
        )

        # "hover to see effects" message
        self.elements["info_default"] = pygame_gui.elements.UITextBox(
            "screens.make_clan.cruel_card_info_placeholder",
            ui_scale(pygame.Rect((-132, 7), (376, 106))),
            object_id=get_text_box_theme("#text_box_30_horizcenter"),
            manager=MANAGER,
            anchors={
                "centerx": "centerx",
                "top_target": self.elements["frame"],
            },
        )

        self.elements["code_info_container"] = UIContainer(
            ui_scale(pygame.Rect((-93, 5), (380, 110))),
            manager=MANAGER,
            anchors={
                "centerx": "centerx",
                "top_target": self.elements["frame"],
            },
            visible=False,
        )

        self.elements["code_title"] = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((0, 2), (376, -1))),
            object_id=get_text_box_theme("#text_box_30_horizleft"),
            manager=MANAGER,
            container=self.elements["code_info_container"],
        )

        self.elements["code_description"] = UITextBoxTweaked(
            "",
            ui_scale(pygame.Rect((0, 8), (376, 80))),
            object_id=get_text_box_theme("#text_box_22_horizleft_spacing_95"),
            manager=MANAGER,
            container=self.elements["code_info_container"],
            anchors={"top_target": self.elements["code_title"]},
        )

        self.elements["page_up"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((8, 155), (34, 34))),
            Icon.ARROW_UP,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            starting_height=1,
            anchors={
                "top_target": self.elements["header"],
                "left_target": self.elements["frame"],
            },
            manager=MANAGER,
        )
        self.elements["page_up"].disable()
        self.elements["page_down"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((8, 10), (34, 34))),
            Icon.ARROW_DOWN,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            starting_height=1,
            anchors={
                "top_target": self.elements["page_up"],
                "left_target": self.elements["frame"],
            },
            manager=MANAGER,
        )

        # update the display with codes
        self.update_codes()

        if len(self.hidden_codes) == 0:
            self.elements["page_up"].disable()
            self.elements["page_down"].disable()

    def update_codes(self):
        """
        Updates the code display
        """
        # for ele in self.card_elements.values():
            # ele.kill()
        # self.card_elements.clear()

        codes = [
            "tresspass",
            "loyalty",
            "gathering",
            "defense",
            "kittypet",
        ]

        if not self.shown_codes and not self.hidden_codes:
            self.shown_codes = list(range(min(5, len(codes))))
            self.hidden_codes = list(range(5, len(codes)))

        if "code_list_container" in self.elements:
            self.elements["code_list_container"].kill()

        self.elements["code_list_container"] = UIContainer(
            ui_scale(pygame.Rect((2, 18), (580, 383))),
            object_id="#code_container",
            container=self.elements["code_container"],
            manager=MANAGER,
        )

        previous_container = None

        for position, code_id in enumerate(self.shown_codes):
            code = codes[code_id]

            if code_id in self.selected_codes:
                continue
            else:

                container_args = {
                    "container": self.elements["code_list_container"],
                    "manager": MANAGER
                }

                if previous_container is not None:
                    container_args["anchors"] = {
                        "top_target": previous_container
                    }

                code_container = UIContainer(
                    ui_scale(pygame.Rect((15, 8), (580, 61))),
                    **container_args
                )

                self.elements[f"code_cont{code_id}"] = code_container

                self.code_elements[f"code_button{code_id}"] = UIImageButton(
                    ui_scale(pygame.Rect((0, 0), (580, 60))),
                    "",
                    object_id="#code_select_button",
                    starting_height=3,
                    container=code_container,
                    manager=MANAGER,
                )
                self.code_elements[f"select{code_id}"] = pygame.gui_elements.UIImage(
                    ui_scale(pygame.Rect((508, 12), (34, 34))),
                    pygame.image.load(
                        f"resources/images/moon_new.png"
                    ).convert_alpha(),
                    object_id="#moon_new_button",
                    container=code_container,
                    manager=MANAGER,
                )
                self.code_elements[f"selected{code_id}"] = pygame.gui_elements.UIIMage(
                    ui_scale(pygame.Rect((508, 312), (34, 34))),
                    pygame.image.load(
                        f"resources/images/moon_full.png"
                    ).convert_alpha(),
                    object_id="#moon_full_button",
                    container=code_container,
                    manager=MANAGER,
                    visible=False,
                )
                self.code_elements[f"code_icon{code_id}"] = pygame_gui.elements.UIImage(
                    ui_scale(pygame.Rect((5, 12), (34, 34))),
                    pygame.image.load(
                        f"resources/images/warrior_icon.png"
                    ).convert_alpha(),
                    container=code_container,
                    manager=MANAGER,
                    starting_height=2,
                )
                self.code_elements[f"frame{code_id}"] = pygame_gui.elements.UIImage(
                    ui_scale(pygame.Rect((5, 0), (430, 60))),
                    get_box(BoxStyles.ROUNDED_BOX, (430, 60)),
                    container=code_container,
                    manager=MANAGER,
                    anchors={"left_target": self.code_elements[f"code_icon{code_id}"]},
                    starting_height=1,
                )
                self.code_elements[f"code_name{code_id}"] = pygame_gui.elements.UILabel(
                    ui_scale(pygame.Rect((18, 11), (-1, 35))),
                    f"code.code_names.{code}",
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    container=code_container,
                    manager=MANAGER,
                    anchors={
                        "left_target": self.code_elements[f"code_icon{code_id}"],
                    },
                )
                self.code_elements[f"code_desc{code_id}"] = pygame_gui.elements.UILabel(
                    ui_scale(pygame.Rect((7, 5), (-1, 50))),
                    f"code.code_descriptions.{code}",
                    object_id=get_text_box_theme("#text_box_22_horizcenter_spacing_95"),
                    container=code_container,
                    manager=MANAGER,
                    anchors={
                        "left_target": self.code_elements[f"code_name{code_id}"],
                    },
                )

                previous_container = code_container

        self.last_shown_code = self.shown_codes[-1]
        self.top_shown_code = self.shown_codes[0]
        if len(self.hidden_codes) != 0:
            self.final_code = max(max(self.shown_codes), max(self.hidden_codes))
            self.first_code = min(min(self.shown_codes), min(self.hidden_codes))
        else:
            self.final_code = max(self.shown_codes)
            self.first_code = min(self.shown_codes)

    def rotate_codes(self, up=False):
        """
        rotates the displayed codes
        :param up: whether we make the codes appear to move up 1 slot (False) or down 1 slot (True)
        """
        if up == False:
            removed = self.shown_codes.pop(0)
            self.hidden_codes.append(removed)

            added = self.hidden_codes.pop(0)
            self.shown_codes.append(added)
        else:
            removed = self.shown_codes.pop()
            self.hidden_codes.insert(0, removed)

            added = self.hidden_codes.pop()
            self.shown_codes.insert(0, added)
        self.update_codes()

        self.elements["page_up"].enable()
        self.elements["page_down"].enable()
        if len(self.hidden_codes) == 0:
            self.elements["page_up"].disable()
            self.elements["page_down"].disable()
        if self.last_shown_code == self.final_code:
            self.elements["page_down"].disable()
        if self.first_code == self.top_shown_code:
            self.elements["page_up"].disable()

    def refresh_chosen(self, code_name, add=False):
        """
        Handles checking card limits, conflicts, marking the card as chosen, and updating the displays
        """
        if add == True:
            self.clan_info.code_rules.append(code_name)
            self.selected_codes.append(code_name)
            # self.add_chosen_card(card_name=code_name)
        elif add == False:
            self.clan_info.code_rules.remove(code_name)
            self.selected_codes.remove(code_name)

        self.update_codes()

    def update_card_info(self, code_name: str):
        """
        Takes the name of the card, retrieves its information, and displays it.
        """
        self.elements["info_default"].hide()
        self.elements["code_info_container"].show()

        self.elements["code_title"].set_text(f"code.{code_name}")
        self.elements["code_description"].set_text(
            f"codes.{code_name}"
        )

    def add_chosen_card(self, card_name: str):
        """
        Adds given card to the chosen card display.
        """
        self.elements["next_step"].enable()

        # aiming for 5 cards in each row
        columns = 6

        if card_name in constants.CRUEL_CARDS_DANGER:
            button = "danger"
        elif card_name in constants.CRUEL_CARDS_ORIGIN:
            button = "origin"
        elif card_name in constants.CRUEL_CARDS_BEHAVIOR:
            button = "behavior"
        else:
            button = "environment"

        if len(self.card_icon_elements) < columns:
            # anchor to left element, if there's an existing icon already
            self.card_icon_elements[card_name] = UICruelCardIcon(
                unscaled_position=(0 if not self.card_icon_elements else 5, 0),
                name=card_name,
                container=self.elements["card_icon_container"],
                tool_tip_text="screens.make_clan.cruel_card_icon_remove",
                object_id=f"#card_icon_{button}",
                anchors={"left_target": list(self.card_icon_elements.values())[-1]}
                if self.card_icon_elements
                else None,
            )

        elif len(self.card_icon_elements) >= columns:
            # anchor to one of the top cards and to left element (if one exists)
            self.card_icon_elements[card_name] = UICruelCardIcon(
                unscaled_position=(
                    0 if len(self.card_icon_elements) == columns else 5,
                    5,
                ),
                name=card_name,
                container=self.elements["card_icon_container"],
                tool_tip_text="screens.make_clan.cruel_card_icon_remove",
                object_id=f"#card_icon_{button}",
                anchors={
                    "left_target": list(self.card_icon_elements.values())[-1],
                    "top_target": list(self.card_icon_elements.values())[0],
                }
                if len(self.card_icon_elements) > columns
                else {"top_target": list(self.card_icon_elements.values())[0]},
            )

    def exit_screen(self):
        self.shown_codes = []
        self.hidden_codes = []
        self.first_code = None
        self.top_shown_code = None
        self.last_shown_code = None
        self.last_hidden_code = None
        self.final_code = None

        for ele in self.code_elements.values():
            ele.kill()
        self.code_elements.clear()

        super().exit_screen()
