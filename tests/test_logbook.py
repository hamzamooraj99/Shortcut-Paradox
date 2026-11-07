from fading_trails.logbook import LogBook, read_events


def test_write_and_read(tmp_path):
    lb = LogBook(tmp_path)
    lb.open_day(0)
    lb.write("run_start", setup="1.6")
    lb.open_day(1)
    lb.turn = 3
    lb.write("action", employee="E01", tool="read_ticket", args={"ticket_id": "ALD-101"})
    lb.close()
    ev = read_events(tmp_path)
    assert [e["event"] for e in ev] == ["run_start", "action"]
    assert ev[1]["day"] == 1 and ev[1]["turn"] == 3 and ev[1]["args"]["ticket_id"] == "ALD-101"


def test_reopening_a_day_overwrites_it(tmp_path):
    lb = LogBook(tmp_path)
    lb.open_day(2)
    lb.write("action", employee="E01")
    lb.open_day(2)  # resume after a crash mid-day
    lb.write("day_start")
    lb.close()
    assert [e["event"] for e in read_events(tmp_path)] == ["day_start"]
