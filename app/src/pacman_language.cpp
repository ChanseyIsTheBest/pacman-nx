// PAC-MAN Championship Edition DX: the game's language (pacman-nx 2026-11-03, from nights-nx's nights_language.cpp and
// sa2-nx's sa2_language.cpp). The game picks its text from the system language (XGetLanguage), which the SDK answers from
// user_language. "auto" follows the Switch's system language (on the PC the Windows display language). The game has
// English, Japanese, French, German, Spanish, Italian and both Chinese scripts (geui/X360: _ee _jj _ff _gg _ss _ii _cs
// _ct), so any other system language gives English.

#include "pacman_language.h"

#include <cctype>
#include <string>

#include <rex/cvar.h>
#include <rex/logging.h>

#if defined(__SWITCH__)
#include <switch.h>
#elif defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

REXCVAR_DEFINE_STRING(language, "auto", "PacMan",
                      "Game language: auto (the system language), english, japanese, french, german, spanish, italian, "
                      "schinese, tchinese");

namespace pacman::language {
namespace {

// Xbox 360 language ids (XLanguage).
constexpr unsigned kEnglish = 1, kJapanese = 2, kGerman = 3, kFrench = 4, kSpanish = 5, kItalian = 6, kTChinese = 8,
                   kSChinese = 10;

unsigned SystemLanguage() {
#if defined(__SWITCH__)
  unsigned id = kEnglish;
  if (R_SUCCEEDED(setInitialize())) {
    u64 code = 0;
    SetLanguage language = SetLanguage_ENUS;
    if (R_SUCCEEDED(setGetSystemLanguage(&code)) && R_SUCCEEDED(setMakeLanguage(code, &language))) {
      switch (language) {
        case SetLanguage_JA: id = kJapanese; break;
        case SetLanguage_FR:
        case SetLanguage_FRCA: id = kFrench; break;
        case SetLanguage_DE: id = kGerman; break;
        case SetLanguage_IT: id = kItalian; break;
        case SetLanguage_ES:
        case SetLanguage_ES419: id = kSpanish; break;
        case SetLanguage_ZHCN:
        case SetLanguage_ZHHANS: id = kSChinese; break;
        case SetLanguage_ZHTW:
        case SetLanguage_ZHHANT: id = kTChinese; break;
        default: id = kEnglish; break;
      }
    }
    setExit();
  }
  return id;
#elif defined(_WIN32)
  switch (PRIMARYLANGID(GetUserDefaultUILanguage())) {
    case LANG_JAPANESE: return kJapanese;
    case LANG_FRENCH: return kFrench;
    case LANG_GERMAN: return kGerman;
    case LANG_SPANISH: return kSpanish;
    case LANG_ITALIAN: return kItalian;
    case LANG_CHINESE:
      return SUBLANGID(GetUserDefaultUILanguage()) == SUBLANG_CHINESE_SIMPLIFIED ? kSChinese : kTChinese;
    default: return kEnglish;
  }
#else
  return kEnglish;
#endif
}

}  // namespace

// The language key's Xbox language (the system's for "auto" or an unknown name); the key's name in lower case.
static unsigned Resolve(std::string& name, bool* known) {
  name = REXCVAR_GET(language);
  for (char& c : name) c = char(std::tolower(static_cast<unsigned char>(c)));
  *known = true;
  if (name == "english") return kEnglish;
  if (name == "japanese") return kJapanese;
  if (name == "french") return kFrench;
  if (name == "german") return kGerman;
  if (name == "spanish") return kSpanish;
  if (name == "italian") return kItalian;
  if (name == "schinese") return kSChinese;
  if (name == "tchinese") return kTChinese;
  *known = name == "auto";
  return SystemLanguage();
}

void Apply() {
  std::string name;
  bool known = true;
  const unsigned id = Resolve(name, &known);
  if (!known) REXLOG_WARN("language = \"{}\" is not known: auto is used", name);
  rex::cvar::SetFlagByName("user_language", std::to_string(id));
  REXLOG_INFO("language: {} (Xbox language {})", name, id);
}

// Read from the key itself: the game menu's fonts are made (OnConfigureFonts) before OnPostSetup runs Apply. The key is
// read at start only (the menu writes a new choice for the next one), so this stays what Apply gave the game.
unsigned XLanguage() {
  static const unsigned id = [] {
    std::string name;
    bool known = true;
    return Resolve(name, &known);
  }();
  return id;
}

}  // namespace pacman::language
