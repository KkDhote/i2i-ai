"""Original I2I motion graphics. No screenshots or generated UI claims.

render_scene returns a 1920 x 1080 RGB frame; the bottom 150 pixels are
reserved for the encoder's captions. Run this file to create a contact sheet.
"""
from functools import lru_cache
from pathlib import Path
import json
import math

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1920, 1080
BG = '#22272a'
PANEL = '#2d3438'
SURFACE = '#343c40'
LINE = '#4a5558'
INK = '#edf0e8'
MUTED = '#b7c1bc'
GREEN = '#a6c8ad'
RED = '#e1a49a'
YELLOW = '#e5cc8b'
BLUE = '#a9cde5'
COLORS = [GREEN, BLUE, YELLOW, RED]
FONT_DIR = Path('C:/Windows/Fonts')
SOURCES = {
    '1': 'Horvitz · CHI 1999',
    '2': 'Findlater & McGrenere · CHI 2004',
    '3': 'Amershi et al. · CHI 2019',
    '4': 'Hart & Staveland · NASA-TLX, 1988',
    '5': 'W3C · WCAG 2.2 motion guidance',
    '6': 'Google · Gemini structured outputs',
    '7': 'W3C · Web Animations',
}
_frames = {}


@lru_cache(maxsize=90)
def font(size, kind='regular'):
    name = {'regular': 'segoeui.ttf', 'bold': 'segoeuib.ttf',
            'display': 'georgia.ttf'}.get(kind, 'segoeui.ttf')
    return ImageFont.truetype(str(FONT_DIR / name), size)


def ease(value):
    value = max(0.0, min(1.0, value))
    return 1 - (1 - value) ** 3


def wrap(draw, value, size, width, kind='regular'):
    lines = []
    for paragraph in str(value).split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = f'{line} {word}'.strip()
            if line and draw.textlength(candidate, font=font(size, kind)) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def text(draw, value, xy, size=24, fill=INK, width=None,
         kind='regular', max_lines=None, spacing=1.3):
    lines = wrap(draw, value, size, width, kind) if width else str(value).split('\n')
    if max_lines and len(lines) > max_lines:
        while len(lines) > max_lines and size > 14:
            size -= 1
            lines = wrap(draw, value, size, width, kind)
    y = xy[1]
    for line in lines:
        draw.text((xy[0], y), line, font=font(size, kind), fill=fill)
        y += size * spacing
    return y


def panel(draw, box, fill=PANEL, outline=LINE, radius=18, width=1):
    draw.rounded_rectangle(tuple(map(int, box)), radius=radius,
                           fill=fill, outline=outline, width=width)


def pill(draw, label, x, y, color=GREEN, size=16, fill='#34453a'):
    w = draw.textlength(label, font=font(size, 'bold')) + 28
    panel(draw, (x, y, x + w, y + size + 18), fill, None, 7)
    text(draw, label, (x + 14, y + 6), size, color, kind='bold')
    return w


def arrow(draw, start, end, color=MUTED, width=3):
    draw.line((start, end), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    points = [end]
    for sign in [-1, 1]:
        a = angle + sign * .6
        points.append((end[0] - 14 * math.cos(a), end[1] - 14 * math.sin(a)))
    draw.polygon(points, fill=color)


def tiny_icon(draw, x, y, color, style=0):
    if style % 4 == 0:
        for i in range(2):
            for j in range(2):
                panel(draw, (x + i * 15, y + j * 15, x + i * 15 + 10, y + j * 15 + 10), None, color, 2, 2)
    elif style % 4 == 1:
        draw.line((x, y + 27, x, y + 4), fill=color, width=2)
        draw.line((x, y + 27, x + 28, y + 27), fill=color, width=2)
        draw.line((x + 4, y + 20, x + 11, y + 13, x + 18, y + 16, x + 28, y + 5), fill=color, width=3)
    elif style % 4 == 2:
        draw.ellipse((x, y, x + 27, y + 27), outline=color, width=2)
        draw.line((x + 13, y + 5, x + 13, y + 14, x + 19, y + 18), fill=color, width=2)
    else:
        draw.line((x + 2, y + 13, x + 10, y + 22, x + 28, y + 4), fill=color, width=3)


def header(scene, index, total):
    image = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    panel(draw, (84, 40, 129, 85), GREEN, None, 9)
    tiny_icon(draw, 94, 50, '#233c2c')
    text(draw, 'I2I', (147, 42), 31, INK, kind='bold')
    text(draw, 'INTELLIGENCE TO IMPACT', (218, 53), 17, MUTED)
    text(draw, 'HACKWAVE 3.0', (1635, 52), 18, MUTED)
    draw.line((84, 104, 1836, 104), fill=LINE, width=1)
    for i, color in enumerate([RED, YELLOW, GREEN, BLUE]):
        draw.line((84 + i * 24, 104, 102 + i * 24, 104), fill=color, width=3)
    text(draw, scene.get('kicker', '').upper(), (84, 132), 19, GREEN)
    text(draw, scene.get('title', 'Your work, in focus.'), (84, 177), 59,
         width=1745, kind='display', max_lines=2, spacing=1.12)
    draw.line((84, 862, 1836, 862), fill=LINE, width=1)
    chapter = scene.get('chapter', scene.get('visual', 'Workspace'))
    text(draw, f'{index + 1:02d} / {total:02d}  {chapter}', (84, 880), 18, MUTED)
    references = '  •  '.join(SOURCES.get(str(i), str(i)) for i in scene.get('source_ids', []))
    label = references or 'I2I hackathon prototype · project implementation'
    size = 16 if len(label) > 65 else 18
    available = 1100
    while draw.textlength(label, font=font(size)) > available and size > 13:
        size -= 1
    w = draw.textlength(label, font=font(size))
    text(draw, label, (1836 - w, 882), size, MUTED)
    return image


def takeaways(draw, scene, y=796):
    bullets = scene.get('bullets', [])
    if not bullets:
        return
    # Three short reminders support the narration without repeating a full script.
    bullets = bullets[:3]
    count = len(bullets)
    width = (1752 - (count - 1) * 26) / count
    for i, item in enumerate(bullets):
        x = 84 + i * (width + 26)
        draw.ellipse((x, y + 8, x + 7, y + 15), fill=COLORS[i % 4])
        text(draw, item, (x + 19, y), 20, MUTED, width=width - 20,
             max_lines=2, spacing=1.3)


def intro(draw):
    panel(draw, (84, 320, 690, 747), '#2a3730', '#425748', 24)
    pill(draw, 'ONE GOAL', 115, 352)
    text(draw, '“Prepare for\ntomorrow’s client\nmeeting.”', (115, 428), 42,
         INK, kind='display', width=550, spacing=1.28)
    text(draw, 'A real need. A useful starting point.', (118, 678), 21, MUTED)
    arrow(draw, (725, 535), (827, 535), GREEN, 4)
    panel(draw, (860, 320, 1836, 747), '#293137', '#4e626d', 24)
    text(draw, 'The tools come into view', (899, 353), 30, BLUE, kind='display')
    labels = [('Client context', YELLOW), ('Conversations', BLUE),
              ('Open issues', RED), ('Meeting brief', GREEN)]
    for i, (label, color) in enumerate(labels):
        x = 899 + (i % 2) * 445
        y = 428 + (i // 2) * 123
        panel(draw, (x, y, x + 412, y + 101), SURFACE, LINE, 12)
        tiny_icon(draw, x + 22, y + 27, color, i)
        text(draw, label, (x + 67, y + 25), 25, INK)
        draw.line((x + 67, y + 68, x + 320, y + 68), fill=color, width=3)


def problem(draw):
    left, top = 84, 326
    panel(draw, (left, top, 1080, 745), '#292f33', LINE, 24)
    names = ['Dashboard', 'Clients', 'Reports', 'Projects', 'Messages', 'Filters']
    for i, name in enumerate(names):
        x, y = left + 27 + (i % 3) * 315, top + 28 + (i // 3) * 164
        panel(draw, (x, y, x + 290, y + 143), PANEL, '#485257', 13)
        tiny_icon(draw, x + 19, y + 17, MUTED, i)
        text(draw, name, (x + 60, y + 15), 24, INK)
        for row, length in enumerate([225, 178, 205]):
            draw.line((x + 20, y + 70 + row * 20, x + length, y + 70 + row * 20), fill='#505c61', width=4)
    text(draw, 'Find. Switch. Filter. Assemble.', (117, 692), 22, RED)
    panel(draw, (1120, top, 1836, 745), '#3a302d', '#614841', 24)
    text(draw, 'The goal is clear.\nThe path is scattered.', (1159, 367), 42, INK,
         width=630, kind='display', spacing=1.25)
    for i, (label, color) in enumerate([('Prepare a meeting', YELLOW), ('Investigate usage', BLUE), ('Follow up work', GREEN)]):
        tiny_icon(draw, 1163, 554 + i * 57, color, i)
        text(draw, label, (1210, 552 + i * 57), 26, MUTED)


def aim(draw):
    names = [('Understand', 'Start with a goal', BLUE),
             ('Clarify', 'Ask when uncertain', YELLOW),
             ('Select', 'Choose useful tools', GREEN),
             ('Arrange', 'Keep one coherent page', BLUE),
             ('Explain', 'Show why things appear', RED)]
    width, gap = 321, 36
    for i, (name, desc, color) in enumerate(names):
        x = 84 + i * (width + gap)
        panel(draw, (x, 384, x + width, 652), PANEL, LINE, 18)
        text(draw, f'0{i + 1}', (x + 24, 411), 24, color, kind='bold')
        tiny_icon(draw, x + 24, 463, color, i)
        text(draw, name, (x + 24, 518), 33, INK, kind='display')
        text(draw, desc, (x + 24, 571), 22, MUTED, width=width - 45, max_lines=2)
        if i < 4:
            arrow(draw, (x + width + 7, 500), (x + width + gap - 7, 500), color, 2)
    text(draw, 'A continuing loop, guided by the person doing the work.', (84, 715), 28, GREEN)


def workspace_scaffold(draw, key):
    panel(draw, (84, 317, 1836, 765), '#252d30', LINE, 20)
    text(draw, 'Illustrative walkthrough • sample data', (108, 334), 17, MUTED)
    text(draw, 'ONE PAGE', (1675, 335), 16, GREEN, kind='bold')
    panel(draw, (104, 373, 428, 743), '#29362e', '#475a4c', 12)
    text(draw, 'Your goal', (125, 390), 19, GREEN, kind='bold')
    goal = {'workspace': 'See the bigger picture', 'meeting': 'Prepare tomorrow’s\nclient meeting',
            'usage': 'Investigate a drop\nin active users', 'overdue': 'Review overdue\nproject work',
            'motion': 'Prepare tomorrow’s\nclient meeting'}.get(key, 'See the bigger picture')
    panel(draw, (125, 431, 406, 541), '#34473a', '#536e59', 8)
    text(draw, goal, (142, 447), 23, INK, width=249, max_lines=3)
    labels = ['Client meeting', 'Usage investigation', 'Overdue work']
    selected = {'meeting': 0, 'usage': 1, 'overdue': 2, 'motion': 0}.get(key, -1)
    for i, label in enumerate(labels):
        if i == selected:
            panel(draw, (125, 564 + i * 43, 406, 600 + i * 43), '#415447', None, 6)
        text(draw, label, (139, 569 + i * 43), 18, INK if i == selected else MUTED)
    text(draw, 'Stable intent panel', (125, 709), 16, MUTED)


HOME = [('Overview', (452, 374, 1370, 487), 'overview'),
        ('Performance', (452, 507, 1030, 721), 'trend'),
        ('I2I AI', (1050, 507, 1807, 721), 'assistant')]
WORKSPACE = {
    'workspace': HOME,
    'meeting': [('Client overview', (452, 374, 877, 538), 'client'),
                ('Recent conversations', (897, 374, 1390, 538), 'conversation'),
                ('Meeting brief', (1410, 374, 1807, 721), 'meeting'),
                ('Open issues', (452, 559, 877, 721), 'issues'),
                ('Next actions', (897, 559, 1390, 721), 'actions')],
    'usage': [('Product usage', (452, 374, 1320, 721), 'trend'),
              ('Affected segments', (1340, 374, 1807, 538), 'cohorts'),
              ('Open issues', (1340, 558, 1807, 721), 'issues')],
    'overdue': [('Overdue work', (452, 374, 1320, 595), 'tasks'),
                ('Project blockers', (1340, 374, 1807, 595), 'blockers'),
                ('Next actions', (452, 615, 1807, 722), 'short-actions')],
    'motion': [('Overview', (452, 374, 1030, 487), 'overview'),
               ('Performance', (452, 507, 1030, 721), 'trend'),
               ('I2I AI', (1050, 374, 1807, 721), 'assistant')],
}


def line_chart(draw, box, compact=False):
    x, y, w, h = box
    before = None if compact else [1200, 1260, 1240, 1310, 1290, 1340, 1300]
    after = [48, 59, 54, 68, 64, 73, 78] if compact else [1280, 1220, 1140, 1020, 940, 890, 860]
    maximum = max(after + (before or [])) * 1.12
    for i in range(3):
        yy = y + i * h / 2
        draw.line((x, yy, x + w, yy), fill=LINE, width=1)
    pts = lambda values: [(x + i * w / 6, y + h - v / maximum * h) for i, v in enumerate(values)]
    old = pts(before) if before else []
    for a, b in zip(old[:-1], old[1:]):
        for p in range(0, 8, 2):
            t, t2 = p / 8, min(1, (p + 1) / 8)
            draw.line((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t,
                       a[0] + (b[0] - a[0]) * t2, a[1] + (b[1] - a[1]) * t2), fill=MUTED, width=2)
    current = pts(after)
    draw.line(current, fill=BLUE, width=3)
    for point in current:
        draw.ellipse((point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3), fill=BLUE)
    if not compact:
        text(draw, 'Sample comparison — timing is not proof of causation.', (x, y + h + 12), 17, MUTED)


def workspace_card(draw, title, rect, kind, fade=1):
    x1, y1, x2, y2 = map(int, rect)
    w, h = x2 - x1, y2 - y1
    color = RED if kind in {'issues', 'tasks', 'blockers'} else YELLOW if kind in {'meeting', 'client'} else BLUE if kind in {'trend', 'assistant', 'cohorts'} else GREEN
    panel(draw, rect, '#323c40', LINE, 10)
    draw.line((x1 + 17, y1 + 1, x2 - 17, y1 + 1), fill=color, width=3)
    title_size = 22 if w > 500 else 20
    text(draw, title, (x1 + 20, y1 + 14), title_size, INK, width=w - 42, max_lines=1)
    x, y = x1 + 20, y1 + 56
    if kind == 'overview':
        for i, (value, label) in enumerate([('2', 'Tasks'), ('0', 'Completed'), ('2', 'Remaining')]):
            xx = x + i * (w - 35) / 3
            text(draw, value, (xx, y - 3), 32, color, kind='display')
            text(draw, label, (xx + 43, y + 9), 17, MUTED)
    elif kind == 'trend':
        if h > 220:
            text(draw, '860', (x, y), 42, BLUE, kind='display')
            text(draw, 'illustrative active users', (x + 87, y + 17), 18, MUTED)
            line_chart(draw, (x, y + 65, w - 40, h - 157))
        else:
            line_chart(draw, (x, y + 9, w - 40, h - 102), True)
    elif kind == 'assistant':
        text(draw, 'What needs your attention?', (x, y), 25, BLUE, kind='display', width=w - 40, max_lines=2)
        panel(draw, (x, y + 59, x2 - 20, y + 105), '#394d5b', '#506879', 6)
        text(draw, 'Summarize our task progress', (x + 13, y + 70), 18, INK)
        if h > 250:
            text(draw, 'Your draft stays with the workspace.', (x, y + 137), 18, MUTED, width=w - 40, max_lines=2)
            panel(draw, (x, y2 - 68, x2 - 20, y2 - 24), '#29353e', '#526d7d', 6)
            text(draw, 'Ask about your tasks…', (x + 12, y2 - 58), 18, MUTED)
    elif kind == 'client':
        text(draw, 'Northstar Labs', (x, y), 27, YELLOW, kind='display')
        text(draw, 'Sample account · onboarding concerns', (x, y + 47), 17, MUTED, width=w - 40, max_lines=2)
    elif kind == 'conversation':
        text(draw, 'Recent feedback', (x, y), 20, BLUE)
        text(draw, 'Onboarding needs attention.\nExports have been slower.', (x, y + 33), 18, MUTED, width=w - 40, max_lines=2)
    elif kind == 'meeting':
        for i, item in enumerate(['Confirm client goals', 'Discuss onboarding', 'Review open issues', 'Agree next owners']):
            text(draw, f'0{i + 1}', (x, y + i * 65), 22, YELLOW, kind='display')
            text(draw, item, (x + 44, y + i * 65 + 2), 18, INK, width=w - 90, max_lines=2)
    elif kind == 'cohorts':
        for i, (label, length) in enumerate([('New users', .5), ('Returning users', 500 / 640)]):
            text(draw, label, (x, y + i * 48), 17, MUTED)
            panel(draw, (x + 185, y + 5 + i * 48, x2 - 20, y + 15 + i * 48), '#4b575b', None, 3)
            panel(draw, (x + 185, y + 5 + i * 48, x + 185 + max(20, (w - 225) * length), y + 15 + i * 48), BLUE, None, 3)
    elif kind == 'tasks':
        text(draw, 'Task', (x, y), 17, MUTED)
        text(draw, 'Owner', (x2 - 239, y), 17, MUTED)
        text(draw, 'Status', (x2 - 126, y), 17, MUTED)
        draw.line((x, y + 31, x2 - 20, y + 31), fill=LINE, width=1)
        text(draw, 'Review quarterly performance', (x, y + 49), 20, INK, width=w - 310)
        text(draw, 'Team', (x2 - 239, y + 51), 18, MUTED)
        pill(draw, 'Overdue', x2 - 126, y + 48, RED, 15, '#513a34')
        text(draw, 'Completed work is excluded from this view.', (x, y + 109), 17, MUTED)
    elif kind == 'blockers':
        text(draw, 'Work waiting on a decision', (x, y), 21, RED, width=w - 40, max_lines=2)
        text(draw, 'Sample blockers help frame\nthe next conversation.', (x, y + 64), 18, MUTED, width=w - 40, max_lines=2)
    elif kind in {'actions', 'short-actions'}:
        text(draw, 'Assign an owner and a due date', (x, y), 19, GREEN, width=w - 40)
        if h > 140:
            text(draw, 'Suggested actions open the real task form.', (x, y + 43), 17, MUTED, width=w - 40, max_lines=2)
    else:
        text(draw, 'Onboarding and export concerns', (x, y), 19, RED, width=w - 40, max_lines=2)
        text(draw, 'Sample issue details', (x, y + 43), 17, MUTED)


def workspace(draw, key, progress=1):
    workspace_scaffold(draw, key)
    target = WORKSPACE.get(key, HOME)
    if key == 'motion':
        for (title, old, kind), (_, new, _) in zip(HOME, target):
            rect = tuple(a + (b - a) * progress for a, b in zip(old, new))
            workspace_card(draw, title, rect, kind)
    else:
        for title, rect, kind in target:
            workspace_card(draw, title, rect, kind)


def architecture(draw):
    items = [('Human', 'State the goal', 'Direction + correction', GREEN),
             ('Gemini', 'Interpret intent', 'Structured JSON plan', BLUE),
             ('FastAPI', 'Validate the plan', 'IDs, widths, unique cards', YELLOW),
             ('React', 'Render useful tools', 'Preserved working state', GREEN)]
    for i, (name, line, detail, color) in enumerate(items):
        x = 84 + i * 449
        panel(draw, (x, 373, x + 405, 664), PANEL, LINE, 18)
        tiny_icon(draw, x + 28, 407, color, i)
        text(draw, name, (x + 28, 469), 39, color, kind='display')
        text(draw, line, (x + 28, 531), 24, INK)
        text(draw, detail, (x + 28, 581), 20, MUTED, width=350, max_lines=2)
        if i < 3:
            arrow(draw, (x + 416, 505), (x + 440, 505), color, 3)
    text(draw, 'A valid format still needs useful choices and grounded context.', (84, 713), 27, MUTED)


def catalog(draw):
    names = ['Overview', 'Performance', 'I2I AI', 'Team tasks', 'Client overview',
             'Conversations', 'Open issues', 'Product usage', 'Segments',
             'Meeting brief', 'Overdue work', 'Blockers', 'Next actions']
    for i, label in enumerate(names):
        col, row = i % 5, i // 5
        x, y = 84 + col * 357, 321 + row * 126
        color = COLORS[i % 4]
        panel(draw, (x, y, x + 324, y + 101), PANEL, LINE, 12)
        tiny_icon(draw, x + 20, y + 20, color, i)
        text(draw, label, (x + 65, y + 21), 22, INK, width=239, max_lines=2)
    pill(draw, '13 CONTROLLED CARDS', 1160, 604, GREEN, 17)
    text(draw, 'Demo-rule fallback  •  Five-minute plan cache', (84, 739), 25, YELLOW)


def control(draw):
    panel(draw, (84, 327, 670, 747), '#2d3b31', '#495e4f', 18)
    pill(draw, 'CLARIFY', 113, 356)
    text(draw, '“Help me prepare.”', (113, 426), 34, INK, kind='display')
    text(draw, 'Which goal should lead?', (113, 499), 26, MUTED)
    for i, label in enumerate(['A client meeting', 'Overdue project work']):
        panel(draw, (113, 566 + i * 61, 641, 612 + i * 61), '#3c4b3f', '#5d7060', 7)
        text(draw, label, (130, 576 + i * 61), 21, INK)
    panel(draw, (704, 327, 1267, 747), '#2c3740', '#4d6270', 18)
    pill(draw, 'EXPLAIN', 733, 356, BLUE, fill='#3a4e5c')
    text(draw, 'Why this card?', (733, 426), 35, INK, kind='display')
    text(draw, 'Open issues are relevant\nto tomorrow’s client\nconversation.', (733, 497), 27, MUTED, width=490)
    panel(draw, (1301, 327, 1836, 747), '#3c362b', '#665a3e', 18)
    pill(draw, 'REFINE', 1330, 356, YELLOW, fill='#51452d')
    text(draw, 'Keep the goal.\nChange the tools.', (1330, 426), 35, INK, kind='display', width=470)
    text(draw, '+ Show overdue work\n− Remove next actions\nReturn to overview', (1330, 555), 25, MUTED, width=467, spacing=1.5)


def chat(draw):
    panel(draw, (84, 320, 1180, 748), '#2b3b48', '#4c6577', 21)
    text(draw, 'I2I AI', (119, 353), 28, BLUE, kind='bold')
    pill(draw, 'LIVE TASK CONTEXT', 853, 350, BLUE, 16, '#3d5568')
    text(draw, 'What needs your attention?', (119, 410), 41, INK, kind='display')
    panel(draw, (119, 488, 1145, 545), '#354e60', '#5e7b91', 8)
    text(draw, 'Summarize our task progress', (138, 503), 25, INK)
    arrow(draw, (1088, 517), (1117, 517), BLUE)
    text(draw, 'Your question', (119, 588), 18, MUTED)
    panel(draw, (119, 627, 1145, 695), '#263743', '#5f7c8f', 8)
    text(draw, 'What should our team prioritize?', (138, 646), 25, INK)
    arrow(draw, (1097, 673), (1097, 646), BLUE)
    for i, (label, detail, color) in enumerate([('Drafts retained', 'Keep typing as cards move', GREEN),
                                               ('Replies retained', 'Bring the assistant back', BLUE),
                                               ('Same work, two themes', 'Green or dark grey', YELLOW)]):
        y = 327 + i * 141
        panel(draw, (1214, y, 1836, y + 119), PANEL, LINE, 13)
        tiny_icon(draw, 1238, y + 27, color, i)
        text(draw, label, (1291, y + 23), 26, color)
        text(draw, detail, (1291, y + 65), 21, MUTED)


def themes(draw):
    for i, dark in enumerate([False, True]):
        x = 84 + i * 910
        surface, ink = (PANEL, INK) if dark else ('#f4f4ed', '#2a4530')
        panel(draw, (x, 326, x + 842, 746), surface, LINE, 20)
        text(draw, 'Dark grey' if dark else 'Present green', (x + 28, 352), 34, ink, kind='display')
        palette = [RED, YELLOW, GREEN, BLUE] if dark else ['#447d54', '#7da273', '#4f7650', '#b0c4a4']
        for j, color in enumerate(palette):
            xx, yy = x + 28 + (j % 2) * 395, 434 + (j // 2) * 135
            panel(draw, (xx, yy, xx + 367, yy + 112), '#394448' if dark else '#fffef8', '#53645d' if dark else '#ced8c6', 10)
            tiny_icon(draw, xx + 20, yy + 25, color, j)
            draw.line((xx + 65, yy + 31, xx + 275, yy + 31), fill=color, width=4)
            draw.line((xx + 65, yy + 61, xx + 290, yy + 61), fill='#7f9890' if dark else '#adbda4', width=3)


def research(draw, scene):
    ids = [str(i) for i in scene.get('source_ids', ['1', '2'])]
    principles = {
        '1': ('Human + AI', 'Direction and automation\nwork together.', GREEN, 'Horvitz, 1999'),
        '2': ('Change has a cost', 'Adaptation is not\nautomatically helpful.', RED, 'Findlater & McGrenere, 2004'),
        '3': ('Explain + correct', 'Relevant context.\nEasy correction.', BLUE, 'Amershi et al., 2019'),
        '4': ('Measure workload', 'Mental demand, effort\nand frustration.', YELLOW, 'Hart & Staveland, 1988'),
        '5': ('Optional motion', 'Respect reduced-motion\npreferences.', GREEN, 'W3C, WCAG 2.2'),
        '6': ('Validate meaning', 'Structured format\nis one boundary.', BLUE, 'Google documentation'),
        '7': ('Control animation', 'Timing, playback\nand cancellation.', GREEN, 'W3C, Web Animations'),
    }
    count = len(ids)
    width = (1752 - (count - 1) * 34) / count
    for i, key in enumerate(ids):
        title, desc, color, author = principles[key]
        x = 84 + i * (width + 34)
        panel(draw, (x, 345, x + width, 703), PANEL, LINE, 20)
        tiny_icon(draw, x + 29, 379, color, i)
        text(draw, title, (x + 29, 449), 35, color, kind='display', width=width - 58, max_lines=2)
        text(draw, desc, (x + 29, 524), 26, INK, width=width - 58, max_lines=3)
        text(draw, author, (x + 29, 645), 18, MUTED, width=width - 58, max_lines=2)
    text(draw, 'Literature-informed design. I2I user-study results are not yet available.', (84, 735), 24, YELLOW)


def priority(draw):
    pill(draw, 'PROPOSED · NOT IMPLEMENTED', 84, 310, YELLOW, 18, '#4a432d')
    text(draw, 'P = 0.35U + 0.30I + 0.20D + 0.15B', (84, 371), 45, INK, kind='display')
    labels = [('U', 'Urgency', 35, BLUE), ('I', 'Business impact', 30, GREEN),
              ('D', 'Dependency', 20, YELLOW), ('B', 'Delay risk', 15, RED)]
    x = 84
    for code, label, weight, color in labels:
        width = 1752 * weight / 100
        draw.rectangle((x, 453, x + width - 7, 510), fill=color)
        text(draw, f'{code}  {weight}%', (x + 19, 466), 23, '#29322b', kind='bold')
        text(draw, label, (x + 2, 527), 22, MUTED)
        x += width
    examples = [('Quarterly review', '75 / 80 / 60 / 70', '72.75', 'High', GREEN),
                ('Productivity analysis', '30 / 80 / 20 / 35', '43.75', 'Medium', YELLOW)]
    for i, (label, values, result, tier, color) in enumerate(examples):
        x = 84 + i * 892
        panel(draw, (x, 595, x + 860, 750), PANEL, LINE, 13)
        text(draw, label, (x + 25, 616), 26, INK)
        text(draw, f'U / I / D / B: {values}', (x + 25, 662), 20, MUTED)
        text(draw, result, (x + 625, 609), 46, color, kind='display')
        text(draw, f'{tier} priority', (x + 627, 675), 20, color)


def evaluation(draw):
    variants = [('Fixed dashboard', '#34393e', MUTED), ('Adaptive workspace', '#2e3e33', GREEN)]
    for i, (label, surface, color) in enumerate(variants):
        x = 84 + i * 896
        panel(draw, (x, 337, x + 856, 513), surface, LINE, 18)
        text(draw, label, (x + 29, 367), 35, color, kind='display')
        text(draw, 'Same tasks. Equivalent data. Balanced order.', (x + 29, 436), 23, INK)
    measures = [('Accuracy', GREEN), ('Completion time', BLUE), ('Navigation effort', YELLOW), ('Workload', RED), ('Unwanted changes', BLUE)]
    for i, (label, color) in enumerate(measures):
        x = 84 + i * 357
        panel(draw, (x, 560, x + 324, 718), PANEL, LINE, 13)
        tiny_icon(draw, x + 22, 583, color, i)
        text(draw, label, (x + 22, 640), 24, INK, width=275, max_lines=2)


def closing(draw):
    items = [('TODAY', 'Working prototype', 'Adaptive cards, live task tools,\nsample business context.', GREEN),
             ('NEXT', 'Connect and persist', 'Persistent storage, real data,\nvalidated priority scoring.', BLUE),
             ('THEN', 'Test the impact', 'Accuracy, time, workload\nand unwanted changes.', YELLOW)]
    for i, (label, title, detail, color) in enumerate(items):
        x = 84 + i * 599
        panel(draw, (x, 325, x + 554, 613), PANEL, LINE, 18)
        text(draw, label, (x + 28, 352), 18, color, kind='bold')
        text(draw, title, (x + 28, 408), 33, INK, kind='display', width=490, max_lines=2)
        text(draw, detail, (x + 28, 487), 23, MUTED, width=480, max_lines=3)
        if i < 2:
            arrow(draw, (x + 563, 462), (x + 589, 462), color)
    text(draw, 'State the work. Let the workspace follow.', (84, 667), 44, GREEN, kind='display')
    text(draw, 'A distinctive combination — with outcomes still to be evaluated.', (84, 731), 24, MUTED)


def _draw_content(draw, scene, progress=1):
    key = scene.get('visual', scene.get('key', 'intro'))
    if key in WORKSPACE:
        workspace(draw, key, progress)
    elif key == 'intro': intro(draw)
    elif key == 'problem': problem(draw)
    elif key == 'aim': aim(draw)
    elif key == 'architecture': architecture(draw)
    elif key == 'catalog': catalog(draw)
    elif key == 'control': control(draw)
    elif key == 'chat': chat(draw)
    elif key == 'themes': themes(draw)
    elif key == 'research': research(draw, scene)
    elif key == 'priority': priority(draw)
    elif key == 'evaluation': evaluation(draw)
    elif key in {'closing', 'roadmap'}: closing(draw)
    else: aim(draw)
    if key != 'priority':
        takeaways(draw, scene)
    else:
        text(draw, 'Deterministic calculation • user-confirmed estimates • weights require validation', (84, 797), 23, MUTED)


def motion_windows(scene, duration):
    """Intervals that need unique frames; all other frames can be held by encoder."""
    windows = [(0.0, 1.6)]
    if scene.get('visual') == 'motion':
        start = max(3, duration * .3)
        windows.append((start, start + .48))
    return windows


def render_scene(scene: dict, elapsed: float, duration: float, index: int, total: int):
    """Render safe original diagrams, with one purposeful transition per scene."""
    signature = (json.dumps(scene, sort_keys=True, ensure_ascii=False), index, total)
    if signature not in _frames:
        base = header(scene, index, total)
        final = base.copy()
        _draw_content(ImageDraw.Draw(final), scene)
        first = final
        if scene.get('visual') == 'motion':
            first = base.copy()
            _draw_content(ImageDraw.Draw(first), scene, 0)
        _frames[signature] = (base, first, final)
    base, first, final = _frames[signature]
    if scene.get('visual') == 'motion':
        start = max(3, duration * .3)
        p = ease((elapsed - start) / .48)
        if p <= 0:
            image = first
        elif p >= 1:
            image = final
        else:
            image = base.copy()
            _draw_content(ImageDraw.Draw(image), scene, p)
    else:
        image = final
    if elapsed < 1.6:
        image = Image.blend(base, image, ease((elapsed - .18) / 1.25))
    return image.copy()


if __name__ == '__main__':
    directory = Path(__file__).resolve().parent
    scenes = json.loads((directory / 'storyboard.json').read_text(encoding='utf-8'))
    thumb_width, thumb_height = 640, 360
    rows = math.ceil(len(scenes) / 4)
    sheet = Image.new('RGB', (thumb_width * 4, thumb_height * rows), '#171b1d')
    for i, scene in enumerate(scenes):
        preview = render_scene(scene, 20, 40, i, len(scenes))
        assert preview.mode == 'RGB' and preview.size == (WIDTH, HEIGHT)
        assert all(low == high for low, high in preview.crop((0, 930, WIDTH, HEIGHT)).getextrema()), 'Caption band must remain empty'
        sheet.paste(preview.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS),
                    ((i % 4) * thumb_width, (i // 4) * thumb_height))
    path = directory / 'visual-preview.png'
    sheet.save(path)
    print(path)
