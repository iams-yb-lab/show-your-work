# Voiceover script — Precision Temperature Controller

Run time 5:38.1 (338 s). 704 words, ~125 words per minute including pauses.

Each line is timed to the visual it belongs to. Start speaking at the timecode; the number in brackets is how long you have before the next line, so you can pace it without rushing.

## Opening  (0:00.0 – 0:18.9)

**0:01.2**  [6.7s]  A laser only stays injection-locked while its frequency sits inside the master’s locking range.

**0:07.8**  [7.1s]  That frequency follows the laser’s temperature. Let the temperature wander, and the lock is gone.

**0:15.0**  [4.9s]  So the instrument has one job: hold the temperature still.


## Target  (0:18.9 – 0:42.3)

**0:19.9**  [3.1s]  How still? Zoom in.

**0:22.9**  [4.2s]  Past a kelvin. Past fifty millikelvin.

**0:27.1**  [7.8s]  One millikelvin, peak to peak, across a continuous one-hour hold — the whole window you see here.

**0:35.0**  [8.0s]  Everything in the design serves that number — under four constraints: cheap, easy to manufacture, modular, simple.


## The loop  (0:42.3 – 1:21.6)

**0:43.0**  [3.3s]  The instrument is a closed loop.

**0:46.3**  [5.9s]  A thermistor senses the laser’s temperature; its resistance falls as it warms.

**0:52.2**  [5.0s]  A front end turns that resistance into a voltage ratio.

**0:57.1**  [5.1s]  An AD7124-8 converter turns the ratio into a 24-bit number.

**1:02.2**  [8.3s]  A Teensy 4.1 compares it with the setpoint and runs the PID locally — never over the network.

**1:10.5**  [7.2s]  Its PWM command drives a MAX1968, which pushes current through a thermoelectric cooler, either direction.

**1:17.7**  [4.9s]  Heat moves, the thermistor sees it, and the loop closes.


## Three stabilities  (1:21.6 – 1:52.6)

**1:22.6**  [3.4s]  Three different things get called stability.

**1:26.0**  [7.5s]  Resolution and short-term noise: can it see a tiny change, and how much do readings jump?

**1:33.5**  [5.8s]  Drift: the real temperature holds, but the reported number slowly moves.

**1:39.3**  [5.5s]  And absolute accuracy: how close the reading is to the truth.

**1:44.8**  [9.0s]  Accuracy we can live without — the working point is found on the bench. Drift is the one that matters.


## The blind term  (1:52.6 – 2:40.9)

**1:53.8**  [2.3s]  Here is why.

**1:56.0**  [9.9s]  The controller can only act on the number the electronics give it. It heats or cools until that number matches the setpoint.

**2:05.9**  [7.6s]  Now suppose the real temperature has not changed, but the electronics slowly begin to report high.

**2:13.5**  [7.5s]  The controller believes it, and cools the laser until the displayed value returns to the setpoint.

**2:21.0**  [5.9s]  The reading now looks perfect. The laser is colder than it was.

**2:27.0**  [8.8s]  That error happens before the reading reaches the controller, so the loop cannot see it. More gain cannot help.

**2:35.8**  [6.7s]  Which is why most of the design effort goes into stopping the reading from wandering.


## The ruler  (2:40.9 – 3:13.6)

**2:42.5**  [3.6s]  The main tool is ratiometric measurement.

**2:46.1**  [8.7s]  The converter does not report volts. It reports the signal as a fraction of a reference — a ruler.

**2:54.9**  [7.5s]  Arrange the circuit so a change moves the signal and the ruler equally, and it cancels.

**3:02.4**  [5.5s]  Move only one, and it looks exactly like a temperature change.

**3:07.9**  [7.3s]  For scale: at 25 °C, one millikelvin is 44 parts per million of the thermistor’s resistance.


## Four arms  (3:13.6 – 4:15.2)

**3:15.2**  [6.9s]  Rather than argue about the best arrangement, the comparison board carries four of them.

**3:22.1**  [10.4s]  Arm one drives the thermistor with the converter’s own current and rules it against a 22 kΩ resistor, so current drift cancels.

**3:32.5**  [8.7s]  But that ruler is also a ceiling: once the thermistor passes 22 kΩ — around 8 °C — the reading clips.

**3:41.2**  [13.0s]  Arm two is a divider from a precision 2.5 V reference, measured against the whole divider — so the source, its buffer and the track drop all cancel.

**3:54.2**  [7.1s]  Arms three and four are one divider with two power sources, chosen by a jumper.

**4:01.2**  [5.6s]  Three’s divider supply and its ruler are independent, so nothing cancels.

**4:06.8**  [9.9s]  Any drift between them lands straight on the reading — one kelvin of board change eats the entire budget. Three is out.


## Arm 2 vs arm 4  (4:15.2 – 5:01.3)

**4:16.7**  [10.3s]  Arm one has no clear edge in drift or in channel count, and its range is bounded — so it steps aside too.

**4:27.0**  [5.1s]  That leaves two and four, and they are genuinely tied.

**4:32.1**  [8.0s]  Arm two has the lowest costed drift — about 0.21 millikelvin for every kelvin the board moves.

**4:40.1**  [7.2s]  But its ruler needs a dedicated reference input pin, so it stops at two channels.

**4:47.3**  [9.3s]  Arm four gives up a little drift and needs no reference pins at all — so it scales to eight.

**4:56.6**  [6.6s]  Precision against expandability. The board is how we find out which we would rather have.


## Why it matters  (5:01.3 – 5:38.1)

**5:03.2**  [3.2s]  Why build it at all?

**5:06.4**  [9.6s]  Commercial laser temperature controllers are expensive — easily over a thousand dollars — and their performance you simply have to trust.

**5:16.0**  [8.4s]  A laser’s frequency depends on current and temperature. Control those two, and the whole system gets dramatically simpler.

**5:24.3**  [6.8s]  And a temperature controller is versatile equipment — useful far beyond one lab.

**5:31.1**  [7.0s]  The design, the calculations and the board are all open. Come build it with us.

