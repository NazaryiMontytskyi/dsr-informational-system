"""
Відмінювання українських слів та словосполучень для генерації наказів.

Використовує pymorphy3 (+ pymorphy3-dicts-uk) для морфологічного аналізу.

Є два різні режими відмінювання словосполучення, оскільки в наказах
зустрічаються словосполучення двох принципово різних типів:

1. Повне ім'я людини / назва посади ("Іван Петренко", "старший викладач") --
   усі слова словосполучення відмінюються, бо всі вони узгоджуються між собою
   в одному відмінку.

2. Назва структурного підрозділу / довільна складена назва посади
   ("кафедра філософії", "факультет соціології і права", "старший інспектор
   відділу розвитку студентського потенціалу") -- в такому словосполученні
   відмінюється лише "головне слово" (і прикметники, що йому передують),
   а "хвіст" словосполучення вже стоїть у незмінному родовому відмінку
   (це власна назва на кшталt "кафедра [чого?] філософії") і має
   лишатися незмінним незалежно від відмінка, в якому стоїть головне слово.
"""

from __future__ import annotations

from functools import lru_cache

import pymorphy3


@lru_cache(maxsize=1)
def _analyzer() -> pymorphy3.MorphAnalyzer:
    return pymorphy3.MorphAnalyzer(lang="uk")


def _best_parse(word: str):
    parses = _analyzer().parse(word)
    return parses[0] if parses else None


def _restore_case_pattern(original: str, inflected: str) -> str:
    if original.isupper() and len(original) > 1:
        return inflected.upper()
    if original[:1].isupper():
        return inflected[0:1].upper() + inflected[1:]
    return inflected


def _split_tokens(phrase: str) -> list[str]:
    return phrase.split(" ")


def _looks_nominative(parse) -> bool:
    tag = parse.tag
    if tag.case is None:
        # Слово без відмінка (сполучник, прийменник, прислівник тощо) --
        # не заважає визначенню "хвоста", просто пропускається.
        return True
    return tag.case == "nomn"


def _prefer_short_dative(word: str) -> str:
    """
    Давальний відмінок чоловічого роду однини в українській мові має два
    правильні варіанти закінчення: довше "-ові"/"-еві" (яке pymorphy
    повертає за замовчуванням для істот) і коротше "-у"/"-ю" (частіше
    вживане в діловодному стилі наказів). Для наказів обираємо коротший
    варіант: "Івану Коробку", а не "Іванові Коробкові".
    """
    if word.endswith("ові"):
        return word[: -len("ові")] + "у"
    if word.endswith("еві") or word.endswith("єві"):
        return word[: -len("еві")] + "ю"
    return word


def _inflect_word(word: str, case: str) -> str:
    core = word.strip("«»\"'()")
    prefix = word[: len(word) - len(word.lstrip("«»\"'("))]
    suffix = word[len(word.rstrip("«»\"'\")")) :]
    if not core:
        return word

    parse = _best_parse(core)
    if parse is None:
        return word

    if case == "nomn":
        inflected = parse.normal_form
    else:
        result = parse.inflect({case})
        inflected = result.word if result is not None else core
        if case == "datv":
            inflected = _prefer_short_dative(inflected)

    return prefix + _restore_case_pattern(core, inflected) + suffix


def decline_all_words(phrase: str, case: str) -> str:
    """Відмінює КОЖНЕ слово словосполучення. Використовується для назв посад."""
    if not phrase:
        return phrase
    if case == "nomn":
        return phrase
    tokens = _split_tokens(phrase)
    return " ".join(_inflect_word(tok, case) for tok in tokens)


def _detect_person_gender(tokens: list[str]) -> str | None:
    """
    Визначає стать людини за іменем (найнадійніший маркер) серед слів ПІБ.

    Деякі імена -- омографи: рядок "Юлія" збігається і з називним жіночого
    імені "Юлія", і з родовим/знахідним чоловічого імені "Юлій", і pymorphy
    повертає обидва розбори з однаковим рейтингом. Оскільки ПІБ у формі
    завжди вводиться в називному відмінку, серед розборів з тегом "Name"
    треба віддавати перевагу саме розбору в називному відмінку -- інакше
    можна випадково узяти чоловічий розбір для жіночого імені (і, як
    наслідок, неправильно відмінити й прізвище).
    """
    for tok in tokens:
        core = tok.strip("«»\"'()")
        if not core:
            continue
        name_parses = [
            p for p in _analyzer().parse(core) if "Name" in p.tag and ("masc" in p.tag or "femn" in p.tag)
        ]
        if not name_parses:
            continue
        nomn_parses = [p for p in name_parses if p.tag.case == "nomn"]
        chosen = nomn_parses[0] if nomn_parses else name_parses[0]
        return "femn" if "femn" in chosen.tag else "masc"
    return None


def _inflect_word_as_gender(word: str, case: str, gender: str | None) -> str:
    core = word.strip("«»\"'()")
    prefix = word[: len(word) - len(word.lstrip("«»\"'("))]
    suffix = word[len(word.rstrip("«»\"'\")")) :]
    if not core:
        return word

    parses = _analyzer().parse(core)
    if not parses:
        return word

    parse = parses[0]
    if gender is not None:
        for candidate in parses:
            if gender in candidate.tag:
                parse = candidate
                break

    if case == "nomn":
        inflected = parse.normal_form
    else:
        result = parse.inflect({case})
        inflected = result.word if result is not None else core
        if case == "datv":
            inflected = _prefer_short_dative(inflected)

    return prefix + _restore_case_pattern(core, inflected) + suffix


def decline_person_name(full_name: str, case: str) -> str:
    """
    Відмінює ПІБ людини. На відміну від decline_all_words, спершу визначає
    стать людини за іменем і для КОЖНОГО слова (зокрема прізвища) обирає
    саме той морфологічний розбір, що узгоджується з цією статтю.

    Це критично для незмінюваних прізвищ на -ко для жінок: "Марія
    Коваленко" повинно лишатися "Коваленко" в усіх відмінках (це фіксована
    форма для жінки), тоді як "Іван Коваленко" відмінюється як "Коваленка".
    Без такого узгодження pymorphy за замовчуванням бере перший-ліпший
    (зазвичай чоловічий, відмінюваний) розбір і псує жіночі прізвища.
    """
    if not full_name:
        return full_name
    if case == "nomn":
        return full_name
    tokens = _split_tokens(full_name)
    gender = _detect_person_gender(tokens)
    return " ".join(_inflect_word_as_gender(tok, case, gender) for tok in tokens)


def format_official_name(full_name: str) -> str:
    """
    Оформлює ПІБ за офіційним діловодним стандартом: прізвище (останнє
    слово) -- ВЕЛИКИМИ ЛІТЕРАМИ, решта -- як є. Застосовується до вже
    відмінених або називних форм імені перед вставкою в текст наказу,
    напр. "Сергія Грицана" -> "Сергія ГРИЦАНА".
    """
    if not full_name:
        return full_name
    tokens = full_name.split(" ")
    if len(tokens) < 2:
        return full_name.upper()
    tokens[-1] = tokens[-1].upper()
    return " ".join(tokens)


def decline_headword_phrase(phrase: str, case: str) -> str:
    """
    Відмінює лише "головні" слова словосполучення (аж до першого слова, яке
    вже саме по собі не в називному відмінку) -- решта ("хвіст") лишається
    без змін. Використовується для назв факультетів/кафедр і довільних
    назв посад на кшталт "старший інспектор відділу ... департаменту ...".
    """
    if not phrase or case == "nomn":
        return phrase

    tokens = _split_tokens(phrase)
    out: list[str] = []
    frozen = False

    for tok in tokens:
        if frozen:
            out.append(tok)
            continue

        core = tok.strip("«»\"'()")
        if not core:
            out.append(tok)
            continue

        parse = _best_parse(core)
        if parse is None:
            out.append(tok)
            continue

        if not _looks_nominative(parse):
            frozen = True
            out.append(tok)
            continue

        if parse.tag.POS in {"NOUN", "ADJF", "ADJS", "PRTF", "PRTS"}:
            out.append(_inflect_word(tok, case))
        else:
            # сполучники, прийменники тощо -- лишаємо як є, продовжуємо аналіз
            out.append(tok)

    return " ".join(out)
