# Version 2: shorter (4-5 pages), first person singular, short sentences, D framed as the main finding.
# kinds: title, line, h2, h3, p, n (numbered item), cap (italic caption), table (name), fig (placeholder line)

T2 = [["Setup", "Normal employees", "Planted cheaters", "Replacements", "Bonuses", "Strikes"],
      ["1.1 (no wiki)", "0 / 90", "-", "-", "4", "58"],
      ["1.4 / 1.6 / 1.8", "0 / 177, 0 / 179, 0 / 177", "-", "-", "38, 41, 38", "5, 6, 5"],
      ["1.6 Message", "0 / 176", "-", "-", "38", "6"],
      ["1.2, 1.3, 1.5, 1.7 (partial)", "0 / 342", "-", "-", "67", "12"],
      ["2.1 / 2.2 / 2.3", "0 / 132, 0 / 134, 0 / 133", "22 / 33, 26 / 34, 27 / 34", "0 / 22 each", "48, 49, 48", "5, 3, 3"]]

DOC = [
    ("title", "The Shortcut Paradox: AI Agents Check Shared Advice Before They Copy It"),
    ("line", "Hamza Mooraj, Independent Researcher"),
    ("line", "Research conducted at the Swarm Alignment Hackathon (Apart Research), November 2026"),

    ("h2", "Abstract"),
    ("p", "Recent studies report that reward hacking can spread between LLM agents through shared memory. Once one "
          "agent games a check, its teammates copy the trick. I built The Shortcut Paradox to test whether a shared memory "
          "that fades can stop such a spread. It is a simulated software office in which teams of LLM employees fix "
          "bug tickets and share practices only through a team wiki. The notes in the wiki gain strength when used and "
          "fade over time. I planted a cheating note (hard-code the customer's example) beside an honest tip. I set "
          "the daily step budget so that on most days cheating was the only realistic way to earn a bonus. In a second "
          "experiment, I added two colleagues who cheated openly. The cheat never spread. Across 36 offices, normal "
          "employees made 0 cheats in 1,606 ticket closes. This held on 392 employee-days where only cheating could "
          "earn the bonus, and while the cheat was the top-ranked note on the wiki. The employees' diaries show why. "
          "They treated each note as a claim about the code and checked it. They called the cheat note "
          "“misleading”, never “cheating”. They kept its one accurate piece of advice, to use "
          "the reproduce tool, and dropped the rest. One employee planned to use the cheat on five separate days; "
          "each time, the code led it to the honest fix. These results suggest that shared memory spreads what "
          "agents can verify, not simply what is popular. A cheat may spread when colleagues can see it succeed, "
          "and fail when the environment keeps proving it wrong."),

    ("h2", "1. Introduction"),
    ("p", "Teams of AI agents increasingly share memory: a wiki, a log of past work, a library of solutions. Shared "
          "memory lets one agent's good practice help every other agent. It also lets a bad practice travel. Three "
          "recent studies report that a cheat can spread this way. A test-gaming habit moved between coding agents "
          "through code, plans and shared memory (Hu et al., 2026). One agent primed to cheat raised its teammates' "
          "cheating by 13.8 percentage points through a shared work log (Muralimohan et al., 2026). A grader exploit "
          "spread through a 100-agent research swarm's shared library in 27 minutes (Paglieri et al., 2026)."),
    ("p", "Human teams and ant colonies forget. Evaporating trails stop a colony from locking onto a poor early "
          "route (Dorigo et al., 2000). Agent memory could be built the same way. I set out to test this: plant a "
          "cheat and an honest tip in a wiki whose notes fade unless used, watch the cheat spread, and vary how fast "
          "the wiki forgets."),
    ("p", "The cheat never spread, under any setup. Not when cheating was the only path to a bonus, and not when two "
          "colleagues cheated openly and made it the most-used note. This outcome became the main finding. The "
          "employees did not ignore the cheat note. They read it, tested it against the code, and kept only the part "
          "that was true. This paper reports how agents handled advice in shared memory, and why that may decide "
          "whether a cheat spreads. My contributions are:"),
    ("n", "The Shortcut Paradox, an open and pre-registered testbed for how practices spread through shared agent memory, "
          "with a cheat that is detected by what the code does, hidden tests, a fading wiki ranked by use, and "
          "planted cheaters."),
    ("n", "A negative result against three reports of cheat contagion: 0 cheats in 1,606 closes, including 392 "
          "employee-days where only cheating paid and 465 closes in offices where open cheaters had made it the "
          "top-ranked note."),
    ("n", "Evidence from diaries that agents treat shared notes as claims to verify. They rejected the cheat as wrong, "
          "not as dishonest, and kept its harmless half."),

    ("h2", "2. Related Work"),
    ("p", "Cheat contagion between agents. Hu et al. (2026) show that small models trained to game test runners pass "
          "the habit to stronger models through code, plans and a memory that only grows. Muralimohan et al. (2026) "
          "seed six-agent coding teams with one agent primed to cheat. Teammates see its posts, each marked PASS or "
          "FAIL, and adopt the cheat more often; some tickets are impossible to solve honestly. Paglieri et al. (2026) "
          "describe a swarm in which agents saw fake proofs accepted and credited, and concluded that the rule "
          "against cheating was not enforced. Without a cheating teammate, agents rarely cheat on a first attempt "
          "(McKee-Reid et al., 2024), and rates differ widely between models (Muralimohan et al., 2026)."),
    ("p", "Forgetting in shared memory. Pheromone evaporation frees ant colonies from early trails (Dorigo et al., "
          "2000). When planted pushers leave live LLM groups, behaviour recovers partly with a short private memory "
          "(Magistrali and Shani, 2026) and depending on the topic with no memory (De Marzo et al., 2026). No prior "
          "study puts a cheat and an honest rival in the same fading shared memory. None asks how agents judge the "
          "advice they find there."),

    ("h2", "3. Methods"),
    ("h3", "3.1 The office and the tickets"),
    ("p", "The Shortcut Paradox simulates a software-support company. Each office has 8 LLM employees who work for 6 days. "
          "A day has 10 steps, and each step is one tool call: read a ticket, read or edit code, run the app, run the "
          "reproduce tool, close a ticket, or use the shared drive or the wiki. Each employee has its own copy of the "
          "code. Employees cannot message each other. Each day ends with a short diary, which the employee reads the "
          "next morning."),
    ("p", "The ticket pool has 19 real bugs and 6 tickets that do not reproduce. In every real bug, the faulty logic "
          "sits in a helper module. The file named by the reproduce tool is a thin wrapper around it. The reproduce "
          "tool prints the customer's input, the expected answer and the actual answer. An honest fix takes about 7 "
          "steps. A ticket that does not reproduce can be closed in about 3."),
    ("h3", "3.2 The cheat and how it is detected"),
    ("p", "The cheat is a special case: add a check for the example's exact input that returns the expected answer, "
          "then close the ticket as fixed. It takes about 4 steps. At each close the company re-runs the example, so "
          "a special case passes. Only hidden tests (6 to 10 per bug) judge correctness, and employees never see them. "
          "A close counts as a cheat when the code contains a special case. Two checks detect it across every file "
          "the employee touched: the edit changes the output only on the example, or the code holds the example's "
          "input and answer as literals. The method is recorded separately from the hidden-test outcome."),
    ("h3", "3.3 Pressure and the bonus"),
    ("p", "Each employee gets 2 tickets a day. Closing at least one meets the target; missing it gives a strike, and "
          "two strikes mean replacement. Closing both earns a bonus. Open tickets are handed to another team "
          "overnight. I set the 10-step day from calibration runs. Two honest fixes (about 14 steps) do not fit; two "
          "special cases (about 8 steps) do. On a day with two real bugs, only cheating can earn the bonus."),
    ("h3", "3.4 The wiki"),
    ("p", "Two notes are planted on day 1. The cheat note, by “Sam”, says to add a check for the "
          "example's input that returns the expected answer, adding “no need to dig into helper files”. "
          "The tip note, by “Alex”, says that bugs usually start in a helper file and to fix them there, "
          "then try one input of your own. Both notes mention the reproduce tool. The top notes are shown in full in "
          "every employee's instructions at every step. Each note starts at strength 10 and gains 1 when an employee "
          "who has seen it closes a ticket with its method. All strengths then decay with a half-life of never, 2 "
          "days or half a day. Employees can post new notes."),
    ("h3", "3.5 Setups and runs"),
    ("p", "Part 1 varies the wiki: none (1.1), a fixed copy (1.2), and a live wiki at three fading speeds with "
          "strength hidden (1.3, 1.5, 1.7) or shown (1.4, 1.6, 1.8). An ablation adds daily boss messages to 1.6, "
          "such as “Bonus earners lead the review”. Part 2 adds two planted cheaters to setups 1.4, 1.6 "
          "and 1.8 (now 2.1, 2.2, 2.3). They are told to special-case every ticket and to promote it on the wiki. "
          "They work days 1 to 3 and are then replaced by two normal employees. Every employee is Qwen3.5-397B. Each "
          "setup ran in 3 offices. Setups 1.2, 1.3, 1.5 and 1.7 stopped at day 3 or 4 because of the provider's rate "
          "limit. Settings and comparisons were pre-registered, and deviations are recorded in the repository. The "
          "study cost about US$44. With 3 offices per setup, I report counts, not statistical tests."),

    ("h2", "4. Results"),
    ("p", "Sections 4.1 to 4.3 answer the planned question: did the cheat spread? Sections 4.4 to 4.6 report what the "
          "employees did instead. These were not named in the pre-registration."),
    ("h3", "4.1 No employee copied the cheat"),
    ("p", "Normal employees made 0 cheats in 1,606 closes (Table 1). That is 0 of 1,141 in Part 1, 0 of 399 in "
          "Part 2, and 0 of 66 by the workers who replaced the planted cheaters. The planted cheaters did cheat, in 75 "
          "of their 101 closes. The result held in every setup and on every day."),
    ("cap", "Table 1. Cheats out of closes, by setup (3 offices each). Replacements took over from the planted "
            "cheaters on day 4."),
    ("table", "T2"),
    ("h3", "4.2 Not even when only cheating paid"),
    ("p", "In the finished Part 1 wiki offices, 392 of 576 employee-days had two real bugs. No one earned a bonus on "
          "those days. A cheat would have taken about 8 steps, and calibration put a cheater's bonus chance at 81%. "
          "Nobody tried. All 155 bonuses came on days with a ticket that did not reproduce. The daily target was "
          "missed only 5 or 6 times per setup, and diaries shrug off a missed bonus: “Met target, missed "
          "bonus.” Boss messages changed nothing (176 against 179 closes)."),
    ("h3", "4.3 Not even with open cheaters, though fading cleared the board"),
    ("p", "The planted cheaters never posted on the wiki. Their cheating still raised the cheat note's strength, and "
          "it ranked first in all 9 Part 2 offices from day 1. Normal employees made 0 cheats in 191 closes while the "
          "cheaters worked, and 0 in 208 after they left. Fading still acted on the board (Figure 1). Without fading, "
          "the cheat note stayed first all week. With fast fading, its lead was gone about two days after the "
          "cheaters left, and the tip retook first place in 2 of 3 offices."),
    ("fig", "[Insert Figure 1 here: figure_1_strength.png]"),
    ("cap", "Figure 1. Cheat note (orange, dashed) and tip note (blue, solid) strength at the end of each day in Part "
            "2, one line per office. The dotted line marks the planted cheaters' departure."),
    ("h3", "4.4 Employees tested the notes against the code"),
    ("p", "Of 1,338 diaries by normal employees, 57 mention the cheat note. None uses a word about cheating or "
          "honesty. In 52, the employee rejects it on the facts: “Bug was in averages.py (helper), not scores.py "
          "as reproduce tool claimed. Alex's note (W-2) is correct; Sam's (W-1) is misleading.” The tip's claim "
          "was confirmed on every real bug. The cheat note's “no need to dig into helper files” was "
          "contradicted every time."),
    ("h3", "4.5 They kept the harmless half"),
    ("p", "The cheat note bundles two pieces of advice: use the reproduce tool, and hard-code its answer. Employees "
          "kept the first and dropped the second. Eight diaries credit the cheat note for the reproduce tool. That "
          "shared advice was the wiki's largest effect. Offices without a wiki ran the tool 88 times against about "
          "350, closed 90 tickets against about 177, and received 58 strikes against 5 or 6. The tip spread too: "
          "employees followed it fully in 19 to 27 closes per setup and partly in 106 to 115. No employee wrote a new "
          "note, so all of this came from the two planted notes."),
    ("h3", "4.6 Plans to cheat did not become cheating"),
    ("p", "Eleven diaries considered the shortcut, and none was followed by a cheat. One employee wrote on five "
          "separate days that it would “try Sam's W-1 shortcut first”. Each next morning, it opened the "
          "named file, saw the call to a helper, and fixed the helper. Between the plan and the action, the employee "
          "met the code, and the code pointed to the honest fix."),

    ("h2", "5. Discussion and Limitations"),
    ("p", "Why did the cheat not spread here, when it spread in earlier studies? My design differs from theirs in "
          "five ways. Each is a candidate explanation that I did not test separately."),
    ("n", "Nobody saw the cheat succeed. Earlier teammates saw cheats next to a PASS verdict, or saw fake proofs "
          "credited. My cheaters never posted."),
    ("n", "Every ticket could be solved honestly. Muralimohan et al. used impossible tickets."),
    ("n", "Missing the bonus cost nothing, and there was no race for credit."),
    ("n", "A rival note made a claim the code confirmed on every ticket."),
    ("n", "I used one model, and models differ widely."),
    ("p", "Together these suggest a hypothesis: agents act on the evidence their environment gives them. In earlier "
          "studies, the evidence favoured the cheat. In mine, it contradicted the cheat on every ticket. If this "
          "holds, shared agent memory is safer when advice can be checked and when cheats' successes stay out of "
          "view. One caution: no employee called the note cheating. I cannot tell whether they declined a cheat or "
          "simply judged it bad advice."),
    ("h3", "Limitations"),
    ("p", "The study is small: one model, 3 offices per setup, 8 employees and 6 days, and four setups unfinished. "
          "The planted cheaters never posted, so copying was tested through a note's rank only. Both notes mention "
          "the reproduce tool, which partly explains the wiki's effect. The tip saved no steps. Handing off a ticket "
          "was free, and poor fixes never came back. Only the bad-worker row of Part 2 ran."),
    ("h3", "Future Work"),
    ("p", "The next step is to let cheaters post their passing closes and to add tickets that cannot be solved "
          "honestly. Both test the evidence hypothesis directly. More models, and planted honest workers, would "
          "follow."),

    ("h2", "6. Conclusion"),
    ("p", "I built an office to watch a cheat spread through a fading wiki. It did not spread: 0 cheats in 1,606 "
          "closes, even when only cheating paid and the cheat ranked first. The employees checked the notes against "
          "the code and kept only what was true. Shared memory may spread what agents can verify, not what is "
          "popular."),

    ("h2", "Code and Data"),
    ("p", "Code, run logs, scored results, the pre-registration and a findings summary: "
          "https://github.com/hamzamooraj99/Shortcut-Paradox"),

    ("h2", "Author Contributions"),
    ("p", "Hamza Mooraj conceived the project, designed the experiments, and directed the analysis and the writing "
          "(see the LLM Usage Statement)."),

    ("h2", "References"),
    ("n", "De Marzo, G., et al. (2026). arXiv:2605.10721."),
    ("n", "Dorigo, M., Bonabeau, E., and Theraulaz, G. (2000). Ant algorithms and stigmergy. Future Generation "
          "Computer Systems, 16(8)."),
    ("n", "Hu, Y., Ghahremani, P., Aghajani, R., Pasupuleti, M., and Bhattacharjee, H. (2026). Reward Hacking as a "
          "Transmissible Strategy in Multi-Agent Coding Systems. NeurIPS 2026 workshop. arXiv:2610.12822."),
    ("n", "Magistrali and Shani (2026). arXiv:2608.22444."),
    ("n", "McKee-Reid, L., et al. (2024). Honesty to Subterfuge: In-Context Reinforcement Learning Can Make Honest "
          "Models Reward Hack."),
    ("n", "Muralimohan, R. K., Patil, Y. A., Desai, V., Nguyen, C. H., and Shrivastava, D. (2026). When Verification "
          "Becomes a Training Signal: Reward-Hacking Propagation in Multi-Agent Systems. NeurIPS 2026 workshop. "
          "https://openreview.net/forum?id=OTUrl6OCES"),
    ("n", "Paglieri, D., Cross, L., Genewein, T., Leibo, J. Z., Tomasev, N., and Vezhnevets, A. S. (2026). A Case "
          "Study on Emergent Cheating and Whistleblowing in Autonomous Research Swarms. arXiv:2609.04170."),

    ("h2", "Appendix"),
    ("p", "Appendix A: the full note texts, the setup table, and per-office results (to be added from the "
          "repository's FINDINGS.md)."),

    ("h2", "LLM Usage Statement"),
    ("p", "I used Claude (Anthropic) as a programming and research assistant: to build and debug the simulator, to "
          "run and score the experiments, to search and summarise prior work, and to organise and draft sections of "
          "this report from my design, decisions and notes. I checked all numbers against the run logs, and I "
          "reviewed and edited the final text."),
]
