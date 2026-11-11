import unittest

from wg_abrechnung import calculate, euro_to_cents, money, settle


class BetragTests(unittest.TestCase):
    def test_gueltige_eingaben(self):
        for text, cents in [("12,50", 1250), ("1.234,56", 123456), ("1,234.56", 123456),
                            ("12.5", 1250), ("7", 700), ("0", 0), ("12,5 €", 1250)]:
            self.assertEqual(euro_to_cents(text), cents, text)

    def test_ungueltige_eingaben(self):
        for text in ["", "abc", "-5", "1.234", "1,234", "nan", "1e3", "12,345"]:
            with self.assertRaises(ValueError, msg=text):
                euro_to_cents(text)

    def test_formatierung(self):
        self.assertEqual(money(123456), "1.234,56 €")
        self.assertEqual(money(5), "0,05 €")


class AbrechnungTests(unittest.TestCase):
    def test_beispiel_aus_readme(self):
        people, total, days, transfers = calculate(
            [("Anna", "120,00", "30"), ("Ben", "0,00", "30"), ("Clara", "60,00", "15")])
        self.assertEqual((total, days), (18000, 75))
        self.assertEqual([p["share"] for p in people], [7200, 7200, 3600])
        self.assertEqual(sorted(transfers), [("Ben", "Anna", 4800), ("Ben", "Clara", 2400)])

    def test_rundung_summe_stimmt(self):
        people, total, _, transfers = calculate(
            [("A", "100,00", "30"), ("B", "0", "30"), ("C", "0", "30")])
        self.assertEqual(sum(p["share"] for p in people), total)
        self.assertEqual(sum(p["balance"] for p in people), 0)
        self.assertEqual(sum(t[2] for t in transfers), 6666)

    def test_ueberweisungen_gleichen_alles_aus(self):
        people, _, _, transfers = calculate(
            [("A", "50", "30"), ("B", "10", "30"), ("C", "0", "30"), ("D", "20", "30"), ("E", "80", "30")])
        bal = {p["name"]: p["balance"] for p in people}
        for von, an, betrag in transfers:
            bal[von] -= betrag
            bal[an] += betrag
        self.assertTrue(all(v == 0 for v in bal.values()))

    def test_minimale_anzahl(self):
        # Zwei unabhängige Paare: 2 Überweisungen statt 3
        transfers = settle([("A", 50), ("B", 30), ("C", -50), ("D", -30)])
        self.assertEqual(len(transfers), 2)

    def test_fehler(self):
        with self.assertRaises(ValueError):
            calculate([("A", "10", "30")])  # nur eine Person
        with self.assertRaises(ValueError):
            calculate([("A", "10", "30"), ("a", "10", "30")])  # doppelter Name
        with self.assertRaises(ValueError):
            calculate([("A", "10", "30"), ("", "5", "30")])  # Betrag ohne Namen
        with self.assertRaises(ValueError):
            calculate([("A", "10", "0"), ("B", "10", "0")])  # 0 Personentage


if __name__ == "__main__":
    unittest.main()
