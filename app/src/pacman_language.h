// pacman-nx (2026-11-03, from nights-nx and sa2-nx): pacman.toml "language" (auto, english, japanese, french, german,
// spanish, italian, schinese, tchinese) as the Xbox language the game reads (user_language).
#pragma once

namespace pacman::language {

// Once the config is loaded, before the game starts.
void Apply();

// pacman-nx (2026-11-25): the Xbox language (XLanguage: 1 English ... ) the game is told, user_language after Apply.
// The game menu's text follows it (game_menu.cpp, where the ultimate base asks rex::system::EffectiveLanguage).
unsigned XLanguage();

}  // namespace pacman::language
