import pygame
import math
import cmath

GASKET_WIDTH = 800
INFO_WIDTH = 650
WIDTH = GASKET_WIDTH + INFO_WIDTH
TOP_MARGIN = 60 
PANEL_HEIGHT = 50
HEIGHT = GASKET_WIDTH + TOP_MARGIN + PANEL_HEIGHT
epsilon = 0.1

log_messages = []
detailed_log_count = 0
allCircles = []
queue = []

state = 0 
c1_base = None
c2_base = None
c3_base = None
preview_circle = None

class Circle:
    def __init__(self, bend, x, y, color=(0, 0, 0)):
        self.bend = bend
        self.radius = abs(1 / bend)
        self.center = complex(x, y)
        self.color = color

    def dist(self, other):
        return abs(self.center - other.center)

    def show(self, surface):
        if self.radius > 1:
            pygame.draw.circle(surface, self.color, (int(self.center.real), int(self.center.imag)), int(self.radius), 2)

def check_tangent(c1, c2):
    d = c1.dist(c2)
    err_ext = abs(d - (c1.radius + c2.radius))
    err_int = abs(d - abs(c1.radius - c2.radius))
    if err_ext < epsilon or err_int < epsilon:
        return True, 0
    return False, min(err_ext, err_int)

def validate(c4, c1, c2, c3):
    if c4.radius < 2:
        return False, "small"
    for other in allCircles:
        d = c4.dist(other)
        if d < epsilon and abs(c4.radius - other.radius) < epsilon:
            return False, "duplicate"
    
    ok1, err1 = check_tangent(c4, c1)
    ok2, err2 = check_tangent(c4, c2)
    ok3, err3 = check_tangent(c4, c3)
    
    if not (ok1 and ok2 and ok3):
        max_err = max(err1, err2, err3)
        if max_err < 10.0:
            return False, f"Відхилено: похибка {max_err:.1f} >= {epsilon}"
        else:
            return False, "extraneous"
            
    return True, "Успішно"

def descartes(c1, c2, c3):
    k1, k2, k3 = c1.bend, c2.bend, c3.bend
    s = k1 + k2 + k3
    prod = k1*k2 + k2*k3 + k1*k3
    root = 2 * math.sqrt(abs(prod))
    return [s + root, s - root]

def complexDescartes(c1, c2, c3, k4):
    k1, k2, k3 = c1.bend, c2.bend, c3.bend
    z1, z2, z3 = c1.center, c2.center, c3.center

    sum_z = k1*z1 + k2*z2 + k3*z3
    root = cmath.sqrt(k1*k2*z1*z2 + k2*k3*z2*z3 + k1*k3*z1*z3) * 2

    return [
        Circle(k4[0], (sum_z + root).real / k4[0], (sum_z + root).imag / k4[0]),
        Circle(k4[0], (sum_z - root).real / k4[0], (sum_z - root).imag / k4[0]),
        Circle(k4[1], (sum_z + root).real / k4[1], (sum_z + root).imag / k4[1]),
        Circle(k4[1], (sum_z - root).real / k4[1], (sum_z - root).imag / k4[1]),
    ]

def nextGeneration():
    global queue, detailed_log_count
    nextQueue = []
    for triplet in queue:
        c1, c2, c3 = triplet
        k4 = descartes(c1, c2, c3)
        newCircles = complexDescartes(c1, c2, c3, k4)
        for nc in newCircles:
            is_valid, reason = validate(nc, c1, c2, c3)
            
            if is_valid:
                log_messages.append(f"[r={nc.radius:.1f}] -> Успішно додано")
                allCircles.append(nc)
                nextQueue.extend([[c1, c2, nc], [c1, c3, nc], [c2, c3, nc]])
            elif reason.startswith("Відхилено"):
                log_messages.append(f"[r={nc.radius:.1f}, x={nc.center.real:.1f}, y={nc.center.imag:.1f}] -> {reason}")
            
            while len(log_messages) > 40:
                log_messages.pop(0)
                    
    queue = nextQueue


def get_c2_from_mouse(pos):
    cx, cy = pos
    M = complex(cx, cy)
    d = abs(M - c1_base.center)
    if d == 0: M += complex(0.1, 0.1); d = abs(M - c1_base.center)
    r1 = c1_base.radius
    
    if d >= r1 - 10: 
        M = c1_base.center + (M - c1_base.center) / d * (r1 - 10)
        d = r1 - 10
        
    r2 = r1 - d
    return Circle(1/r2, M.real, M.imag)

def get_c3_from_mouse(pos):
    F1 = c1_base.center
    F2 = c2_base.center
    r1 = c1_base.radius
    r2 = c2_base.radius
    
    a = (r1 + r2) / 2
    c_dist = abs(F1 - F2) / 2
    b = math.sqrt(max(0, a**2 - c_dist**2))
    
    C_ell = (F1 + F2) / 2
    theta = cmath.phase(F2 - F1) if c_dist != 0 else 0
    
    M = complex(pos[0], pos[1])
    phi = cmath.phase(M - C_ell) - theta
    
    p_unrotated = complex(a * math.cos(phi), b * math.sin(phi))
    C3_center = p_unrotated * cmath.exp(1j * theta) + C_ell
    
    r3 = r1 - abs(C3_center - c1_base.center)
    if r3 < 2: r3 = 2
    return Circle(1/r3, C3_center.real, C3_center.imag)

def reset_builder():
    global allCircles, queue, state, c1_base, c2_base, c3_base, preview_circle, log_messages, detailed_log_count
    allCircles = []
    queue = []
    log_messages = []
    detailed_log_count = 0
    state = 0
    c1_base = Circle(-1 / (GASKET_WIDTH/2), GASKET_WIDTH/2, TOP_MARGIN + (GASKET_WIDTH)/2)
    c2_base = None
    c3_base = None
    preview_circle = None

class Button:
    def __init__(self, rect, text, action):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action
        self.font = pygame.font.SysFont("arial", 26)

    def draw(self, surface):
        pygame.draw.rect(surface, (200,200,200), self.rect)
        pygame.draw.rect(surface, (0,0,0), self.rect, 2)
        label = self.font.render(self.text, True, (0,0,0))
        text_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.action()
                return True
        return False

def draw_instructions(surface):
    font = pygame.font.SysFont("arial", 28)
    if state == 0:
        text = "Крок 1: Рухайте мишкою і клікніть, щоб поставити 1-е внутрішнє коло"
    elif state == 1:
        text = "Крок 2: Рухайте мишкою і клікніть, щоб поставити 2-е коло"
    else:
        text = "Генерація фрактала..."
    
    label = font.render(text, True, (50, 50, 200))
    text_rect = label.get_rect(center=(GASKET_WIDTH // 2, 30))
    surface.blit(label, text_rect)

def draw_info_panel(screen):
    panel_rect = pygame.Rect(GASKET_WIDTH, 0, INFO_WIDTH, HEIGHT)
    pygame.draw.rect(screen, (240, 240, 240), panel_rect)
    pygame.draw.line(screen, (150, 150, 150), (GASKET_WIDTH, 0), (GASKET_WIDTH, HEIGHT), 2)
    
    font_title = pygame.font.SysFont("arial", 28, bold=True)
    font_log = pygame.font.SysFont("consolas", 14)
    font_total = pygame.font.SysFont("arial", 30, bold=True)
    
    y_offset = 20
    title = font_title.render("Логи обчислень (останні 40):", True, (0, 0, 0))
    screen.blit(title, (GASKET_WIDTH + 20, y_offset))
    y_offset += 40
    
    for msg in log_messages:
        color = (0, 150, 0) if "Успішно" in msg else (200, 0, 0)
        lbl = font_log.render(msg, True, color)
        screen.blit(lbl, (GASKET_WIDTH + 20, y_offset))
        y_offset += 18
        
    lbl_total = font_total.render(f"Всього кіл: {len(allCircles)}", True, (0, 100, 0))
    screen.blit(lbl_total, (GASKET_WIDTH + 20, HEIGHT - 55))

def main():
    global allCircles, queue, state, c1_base, c2_base, c3_base, preview_circle
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    pygame.display.set_caption("Pygame")

    reset_builder()

    button_width = 150
    button_height = 40
    spacing = 50
    total_width = button_width*2 + spacing
    start_x = (GASKET_WIDTH - total_width) // 2
    y_pos = HEIGHT - PANEL_HEIGHT + (PANEL_HEIGHT - button_height)//2

    buttons = [
        Button((start_x, y_pos, button_width, button_height), "Скинути", reset_builder),
        Button((start_x + button_width + spacing, y_pos, button_width, button_height), "Закрити", 
               lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)))
    ]

    running = True
    while running:
        screen.fill((255, 255, 255))
        gasket_surface = pygame.Surface((GASKET_WIDTH, HEIGHT-PANEL_HEIGHT))
        gasket_surface.fill((255,255,255))

        if state == 0:
            if c1_base: c1_base.show(gasket_surface)
            if preview_circle: preview_circle.show(gasket_surface)
        elif state == 1:
            if c1_base: c1_base.show(gasket_surface)
            if c2_base: c2_base.show(gasket_surface)
            if preview_circle: preview_circle.show(gasket_surface)
        elif state == 2:
            nextGeneration()
            for c in allCircles:
                c.show(gasket_surface)

        draw_instructions(gasket_surface)
        screen.blit(gasket_surface, (0,0))
        
        draw_info_panel(screen)

        pygame.draw.rect(screen, (220,220,220), (0, HEIGHT-PANEL_HEIGHT, GASKET_WIDTH, PANEL_HEIGHT))
        for b in buttons:
            b.draw(screen)

        pygame.display.flip()
        clock.tick(30 if state != 2 else 10)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            clicked_ui = False
            for b in buttons:
                if b.handle_event(event):
                    clicked_ui = True

            if not clicked_ui:
                if event.type == pygame.MOUSEMOTION or event.type == pygame.MOUSEBUTTONDOWN:
                    if event.pos[1] < HEIGHT - PANEL_HEIGHT and event.pos[0] < GASKET_WIDTH:
                        
                        if event.type == pygame.MOUSEMOTION:
                            if state == 0 and c1_base:
                                preview_circle = get_c2_from_mouse(event.pos)
                            elif state == 1 and c1_base and c2_base:
                                preview_circle = get_c3_from_mouse(event.pos)

                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if state == 0:
                                c2_base = get_c2_from_mouse(event.pos)
                                state = 1
                            elif state == 1:
                                c3_base = get_c3_from_mouse(event.pos)
                                allCircles = [c1_base, c2_base, c3_base]
                                queue = [[c1_base, c2_base, c3_base]]
                                state = 2
                                preview_circle = None

    pygame.quit()

if __name__ == "__main__":
    main()