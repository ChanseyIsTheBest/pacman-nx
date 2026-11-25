// pacman-nx (2026-11-25, the user: "make sure the ingame menu has only items currently in the release toml +
// achivements |p1|p2|p3|p4 tabs at the top + rumble which is on by default ... make sure in game menu also keeps menu
// colour menu opacity and menu font"): the game menu's Settings rows for PAC-MAN (game_menu.h, SetGameMenuRows).
//
// The ultimate base's menu makes a row for each of its keys this build defines; this keeps, in the base's order:
//   language                     the release toml's (pacman_language.cpp: auto, english ... tchinese), * (read at start)
//   input_rumble                 rumble, on by default (the base's port 59)
//   input_xbox_layout            the release toml's
//   input_joycon_sideways        the release toml's
//   input_joycon_sideways_stick  the release toml's
//   menu_color, menu_font, menu_background_opacity   the menu's own look
// The release toml's button maps ([input_p1] a = ...) are the P1 to P4 tabs; the Achievements tab is the base's.
#include "pacman_menu.h"

#include <algorithm>
#include <string>
#include <vector>

#include "game_menu.h"
#include "game_menu_text.h"

namespace pacman::menu {
namespace {

using Setting = blur::GameMenuDialog::Setting;
using Choice = blur::GameMenuDialog::Choice;

constexpr const char* kKeep[] = {"language",       "input_rumble",           "input_xbox_layout",
                                 "input_joycon_sideways", "input_joycon_sideways_stick", "menu_color",
                                 "menu_font",      "menu_background_opacity"};

Choice Quoted(std::string label, std::string raw) {
  std::string toml = "\"" + raw + "\"";
  return {std::move(label), std::move(raw), std::move(toml)};
}

// PAC-MAN's eight languages (the game's own: geui/X360 _ee _jj _ff _gg _ss _ii _cs _ct), by their own names
// (game_menu_text.h's kMenuLanguageNames), as pacman.toml writes them; "auto" is the menu's System.
std::vector<Choice> Languages() {
  struct Language {
    int name;  // kMenuLanguageNames' index
    const char* key;
  };
  static const Language kLanguages[] = {{0, "english"}, {8, "japanese"}, {1, "french"},    {2, "german"},
                                        {4, "spanish"}, {3, "italian"},  {10, "schinese"}, {11, "tchinese"}};
  std::vector<Choice> choices = {Quoted(blur::GameMenuText(blur::C_SYSTEM), "auto")};
  for (const Language& l : kLanguages)
    choices.push_back(Quoted(blur::kMenuLanguageNames[l.name], l.key));
  return choices;
}

void Rows(std::vector<Setting>& settings, int /*language_row*/, const std::string& /*file*/) {
  std::vector<Setting> kept;
  for (const char* key : kKeep) {
    auto it = std::find_if(settings.begin(), settings.end(), [&](const Setting& s) { return s.key == key; });
    if (it == settings.end())
      continue;  // a key this build does not define (the Joy-Con keys on the PC)
    Setting s = std::move(*it);
    if (s.key == "language") {
      s.choices = Languages();
      s.default_choice = 0;
    }
    kept.push_back(std::move(s));
  }
  settings = std::move(kept);
}

}  // namespace

void Install() { blur::SetGameMenuRows(&Rows); }

}  // namespace pacman::menu
