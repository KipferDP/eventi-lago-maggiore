"""Prüfungen der Doppel-Erkennung und Orts-Zuordnung (python -m unittest test_quellen)."""
import unittest

import quellen as q

T = "2026-11-20"


def ev(title, start, frm="", loc="Locarno", end=None):
    return {"title": title, "start": start, "end": end or start, "loc": loc,
            "dates": [{"start": start, "end": end or start, "from": frm, "to": ""}]}


class Doppel(unittest.TestCase):
    def test_gleiche_veranstaltung_andere_sprache(self):
        self.assertTrue(q.is_duplicate(ev("Notte anni 60", "2026-11-20", "21:00"),
                                       ev("60er-Jahre-Nacht", "2026-11-20", "21:00"), T))

    def test_titel_mit_jahr(self):
        self.assertTrue(q.is_duplicate(ev("Winterland", "2026-11-19"),
                                       ev("Winterland 2026/27", "2026-11-19", "10:00", end="2027-01-06"), T))

    def test_gleicher_ort_gleiche_zeit(self):
        self.assertTrue(q.is_duplicate(ev("Mercato di Natale in Città Vecchia", "2026-12-08", "10:00", "Città Vecchia, Locarno"),
                                       ev("Weihnachtsmarkt Locarno, Altstadt", "2026-12-08", "10:00", "Città Vecchia, Locarno"), T))

    def test_verschiedene_events_gleiche_zeit_bleiben(self):
        self.assertFalse(q.is_duplicate(ev("Concerto jazz", "2026-12-05", "20:30", "Teatro di Locarno"),
                                        ev("Il più grande tributo a Mina", "2026-12-05", "20:30", "Kursaal Teatro di Locarno - Largo Zorzi 1, Locarno"), T))

    def test_anderer_tag_bleibt(self):
        self.assertFalse(q.is_duplicate(ev("Breaking Brecht", "2026-11-21", "20:30"),
                                        ev("Breaking Brecht", "2026-11-28", "20:30"), T))

    def test_andere_zeit_bleibt(self):
        self.assertFalse(q.is_duplicate(ev("Il Piccolo Principe", "2026-12-19", "16:00"),
                                        ev("Il Piccolo Principe", "2026-12-19", "20:00"), T))


class Orte(unittest.TestCase):
    def test_mehrere_orte(self):
        self.assertEqual(q.lev_towns("ascona", "Ascona Brissago Gambarogno Locarno"), ["ascona", "locarno"])

    def test_nur_fremder_ort(self):
        self.assertEqual(q.lev_towns("locarno", "Camedo"), [])

    def test_saal_ohne_ort(self):
        self.assertEqual(q.lev_towns("muralto", "Sala Congressi"), ["muralto"])

    def test_region_verzasca_nur_tenero(self):
        self.assertEqual(q.lev_towns(None, "Tenero-Contra"), ["tenero"])
        self.assertEqual(q.lev_towns(None, "Gordola"), [])


class Kategorien(unittest.TestCase):
    def test_feste_vorne(self):
        self.assertEqual(q.cats_for("Concerto di Natale")[0], "weihnachten")
        self.assertEqual(q.cats_for("Capodanno con la RSI")[0], "silvester")

    def test_winterland_dj(self):
        self.assertEqual(q.cats_for("DJ Yan Kings", default="weihnachten"), ["weihnachten", "musik"])


if __name__ == "__main__":
    unittest.main()
