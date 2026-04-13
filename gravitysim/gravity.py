import pygame

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Moji's Gravity Simulator")

# Global simulation settings
PAUSE = False
FPS = 240
TIME_SCALE = 2  # Controls simulation speed
G = 15.0        
VELOCITY_SCALE = 0.15
MAX_LAUNCH_SPEED = 50
GAMESTATE = "MENU"

# Stores all mass objects in the simulation
List_of_Masses = []

dragging_mass = False
drag_start = pygame.Vector2(0, 0)
drag_current = pygame.Vector2(0, 0)

clock = pygame.time.Clock()

USER_BLURB = (
    "This is a simulator that I made as a fun side project to just simulate gravity "
    "with masses to see how well I could do it. Then when I learned that I could "
    "show this off as a piece of work I piled on around 70% of the code with my "
    "own custom classes and GUI based on pygame. In the end though I think it "
    "came out well but there are still things that need to be fixed lot of bugs."
    " Also coordinates are not centered in the normal way with it being based in the"
    " top right corner with x+ to the right and y+ down"
)

# Calculates gravitational force between two masses
def gravitational_force(mass1, mass2):
    distance_vector = mass2.position - mass1.position
    distance = distance_vector.length()

    if distance == 0:
        return pygame.Vector2(0, 0)
    
    # Newton's law 
    force_magnitude = G * (mass1.mass * mass2.mass) / (distance ** 2)
    force_direction = distance_vector.normalize()

    # Softening to avoid extreme forces at very small distances
    softening = mass1.radius + mass2.radius

    if distance < softening:
        normalforce = G * (mass1.mass * mass2.mass) / (softening ** 2)
        force_magnitude = normalforce * (distance / softening)
    
    return force_direction * force_magnitude


class Mass:
    def __init__(self, mass, position, velocity, acceleration, color):
        self.mass = mass
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.acceleration = pygame.Vector2(acceleration)
        self.radius = int(mass ** (1/3))  # Size scales with mass like the real world using cube root
        self.color = color
        self.trail = [] #sStores all previous positions for trail effect
        self.pinned = False  # If True, object does not move
    
    
    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.radius)

    # Draw velocity vector for visualization
    def showvelocity(self):
        end_pos = self.position + self.velocity
        pygame.draw.line(screen, (0, 255, 0), self.position, end_pos, 2)

    # Draw motion trail
    def draw_trail(self):
        for pos in self.trail:
            pygame.draw.circle(screen, (200, 200, 200), (int(pos.x), int(pos.y)), 1)

        # Only update trail when simulation is running
        if not PAUSE:
            self.trail.append(self.position.copy())
            if len(self.trail) > 1000:
                self.trail.pop(0)
    
    #Guys its Newtons second law!
    def apply_force(self, force):
        self.acceleration += force / self.mass

    # Apply gravity from all other masses
    def apply_gravity(self, List_of_Masses):
        for other_mass in List_of_Masses:
            if other_mass != self:
                force = gravitational_force(self, other_mass)
                self.apply_force(force)

    # Update position and velocity using Euler Integration with a semi-implicit method
    def update(self, dt):
        if self.pinned:
            return

        old_acc = self.acceleration
        self.acceleration = pygame.Vector2(0, 0)

        # Semi implicit integration step
        self.velocity += 0.5 * (old_acc + self.acceleration) * dt
        self.position += self.velocity * dt + 0.5 * old_acc * dt * dt

        self.apply_gravity(List_of_Masses)

class Button:
    def __init__(self, rect, text, border_width=2, border_color=(255,255,255)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.border_width = border_width
        self.border_color = border_color

    # Draw button with hover effect
    def draw(self):
        mouse = pygame.mouse.get_pos()
        color = (120,120,120) if self.rect.collidepoint(mouse) else (70,70,70)
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, self.border_color, self.rect, self.border_width, border_radius=8)
        text_surf = pygame.font.SysFont(None, 32).render(self.text, True, (255,255,255))
        screen.blit(text_surf, text_surf.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

class TextBox:
    def __init__(self, x, y, w=140, h=32, font=None, text_color=(255,255,255), color_active='lightskyblue3', color_inactive='chartreuse4', allow_negative=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font or pygame.font.Font(None, 32)
        self.text = ""
        self.text_surface = self.font.render("", True, text_color)
        self.active = False
        self.just_activated = False
        self.allow_negative = allow_negative
        self.color_active = pygame.Color(color_active)
        self.color_inactive = pygame.Color(color_inactive)
        self.color = self.color_inactive
        self.text_color = text_color
        self.enter_pressed = False

    # The stupid number format...
    def valid_number_format(self, new_text):
        if new_text in ("", ".", "-", "-."):
            return self.allow_negative or new_text in ("", ".")
        if "-" in new_text:
            if not self.allow_negative or new_text.count("-") > 1 or not new_text.startswith("-"):
                return False
        core = new_text.lstrip("-")
        if core.count(".") > 1: return False
        left, right = core.split(".", 1) if "." in core else (core, "")
        return not ((left and not left.isdigit()) or (right and not right.isdigit()) or len(left) > 5 or len(right) > 3)

    # Handle keyboard/mouse events
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            was_active = self.active
            self.active = self.rect.collidepoint(event.pos)
            if self.active and not was_active:
                self.just_activated = True

        if event.type == pygame.KEYDOWN and self.active:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.enter_pressed = True
                self.active = False
                self.just_activated = False
                return
            if self.just_activated:
                self.text = ""
                self.just_activated = False
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isdigit() or event.unicode in ".-":
                if self.valid_number_format(self.text + event.unicode):
                    self.text += event.unicode
            self.text_surface = self.font.render(self.text, True, self.text_color)
 
    def update(self):
        self.color = self.color_active if self.active else self.color_inactive

    # Draw textbox with clipped text if too long
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        clipped = self.text_surface
        if clipped.get_width() > self.rect.w - 10:
            clipped = clipped.subsurface(clipped.get_width() - (self.rect.w - 10), 0, self.rect.w - 10, clipped.get_height())
        screen.blit(clipped, (self.rect.x+5, self.rect.y+5))

    def get_text(self): return self.text

    def clear(self):
        self.text = ""
        self.text_surface = self.font.render("", True, self.text_color)

    def submitted(self):
        if self.enter_pressed:
            self.enter_pressed = False
            return True
        return False

class SettingsPanel:
    def __init__(self):
        self.visible, self.x, self.y, self.width, self.height = True, 10, 20, 240, 320
        self.dragging = False
        self.drag_offset = pygame.Vector2(0, 0)
        self.sim_speed_box = TextBox(self.x+20, self.y+60, allow_negative=False)
        self.g_box = TextBox(self.x+20, self.y+110, allow_negative=True)
        self.fps_box = TextBox(self.x+20, self.y+160, allow_negative=False)
        self.show_vectors, self.show_trails = True, True
        self.reset_button = Button((self.x+20, self.y+240, 120, 30), "Reset")
        self.quit_window_button = Button((self.x+210, self.y-0, 30, 30), "X")
        self.clear_all_objects_button = Button((self.x+20, self.y+280, 180, 30), "Clear All")
        self.defaults = {"TIME_SCALE": 2, "G": 15.0, "FPS": 240}
        self.sync_values()

    def sync_positions(self): # Update positions of all UI elements based on panel's current position
        self.sim_speed_box.rect.topleft = (self.x+20, self.y+60)
        self.g_box.rect.topleft = (self.x+20, self.y+110)
        self.fps_box.rect.topleft = (self.x+20, self.y+160)
        self.reset_button.rect.topleft = (self.x+20, self.y+240)
        self.quit_window_button.rect.topleft = (self.x+210, self.y-0)
        self.clear_all_objects_button.rect.topleft = (self.x+20, self.y+280)

    def sync_values(self): #Same idea but for syncing the textboxes
        if not self.sim_speed_box.active:
            self.sim_speed_box.text = str(round(TIME_SCALE, 3))
            self.sim_speed_box.text_surface = self.sim_speed_box.font.render(self.sim_speed_box.text, True, self.sim_speed_box.text_color)
        if not self.g_box.active:
            self.g_box.text = str(round(G, 3))
            self.g_box.text_surface = self.g_box.font.render(self.g_box.text, True, self.g_box.text_color)
        if not self.fps_box.active:
            self.fps_box.text = str(FPS)
            self.fps_box.text_surface = self.fps_box.font.render(self.fps_box.text, True, self.fps_box.text_color)
    
    def handle_event(self, event): #Handle dragging, button clicks, and textbox input
        global TIME_SCALE, G, FPS
        if not self.visible: return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pygame.Rect(self.x, self.y, self.width, 30).collidepoint(event.pos):
                self.dragging = True
                self.drag_offset = pygame.Vector2(event.pos) - pygame.Vector2(self.x, self.y)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            new_pos = pygame.Vector2(event.pos) - self.drag_offset
            self.x, self.y = int(new_pos.x), int(new_pos.y)
            self.sync_positions()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_v: self.show_vectors = not self.show_vectors
            if event.key == pygame.K_c: self.show_trails = not self.show_trails
        if self.reset_button.clicked(event):
            TIME_SCALE, G, FPS = self.defaults["TIME_SCALE"], self.defaults["G"], self.defaults["FPS"]
        if self.quit_window_button.clicked(event): self.visible = False
        if self.clear_all_objects_button.clicked(event): List_of_Masses.clear()
        
        for box in [self.sim_speed_box, self.g_box, self.fps_box]: box.handle_event(event)
        if self.sim_speed_box.submitted(): 
            try: TIME_SCALE = float(self.sim_speed_box.get_text())
            except: pass
        if self.g_box.submitted():
            try: G = float(self.g_box.get_text())
            except: pass
        if self.fps_box.submitted():
            try: FPS = int(float(self.fps_box.get_text()))
            except: pass

    def draw(self, screen): #draws it
        if not self.visible: return
        self.sync_values()
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, (40,40,60), panel_rect, border_radius=10)
        pygame.draw.rect(screen, (200,200,255), panel_rect, 2, border_radius=10)
        pygame.draw.rect(screen, (60,60,90), pygame.Rect(self.x, self.y, self.width, 30), border_radius=10)
        font = pygame.font.Font(None, 24)
        screen.blit(font.render("Settings", True, (255,255,255)), (self.x+10, self.y+5))
        labels = [("Sim Speed:", self.y+45), ("Gravity G:", self.y+95), ("FPS:", self.y+145), (f"Vectors: {'ON' if self.show_vectors else 'OFF'} (V)", self.y+200), (f"Trails: {'ON' if self.show_trails else 'OFF'} (C)", self.y+220)]
        for text, y in labels: screen.blit(font.render(text, True, (255,255,255)), (self.x+20, y))
        for box in [self.sim_speed_box, self.g_box, self.fps_box]:
            box.update()
            box.draw(screen)
        self.reset_button.draw()
        self.quit_window_button.draw()
        self.clear_all_objects_button.draw()

    #helper method to check if click is within panel for event handling
    def is_clicked(self, pos): return pygame.Rect(self.x, self.y, self.width, self.height).collidepoint(pos)

#This was based on the settings panel
class InspectorPanel: 
    def __init__(self):
        self.visible, self.x, self.y, self.width, self.height = False, 300, 50, 240, 420
        self.dragging = False
        self.drag_offset = pygame.Vector2(0, 0)
        self.selected_mass = None
        self.mass_box = TextBox(self.x+20, self.y+55, allow_negative=False)
        self.pos_x_box = TextBox(self.x+20, self.y+115, allow_negative=True)
        self.pos_y_box = TextBox(self.x+20, self.y+165, allow_negative=True)
        self.vel_x_box = TextBox(self.x+20, self.y+225, allow_negative=True)
        self.vel_y_box = TextBox(self.x+20, self.y+275, allow_negative=True)
        self.quit_window_button = Button((self.x+210, self.y, 30, 30), "X")
        self.delete_object_button = Button((self.x+20, self.y+360, 150, 30), "Delete Mass")
        self.pin_button = Button((self.x+20, self.y+320, 150, 30), "Pin Mass")

    def sync_positions(self):
        self.mass_box.rect.topleft = (self.x+20, self.y+55)
        self.pos_x_box.rect.topleft = (self.x+20, self.y+115)
        self.pos_y_box.rect.topleft = (self.x+20, self.y+165)
        self.vel_x_box.rect.topleft = (self.x+20, self.y+225)
        self.vel_y_box.rect.topleft = (self.x+20, self.y+275)
        self.quit_window_button.rect.topleft = (self.x+210, self.y)
        self.delete_object_button.rect.topleft = (self.x+20, self.y+360)
        self.pin_button.rect.topleft = (self.x+20, self.y+320)
    
    def handle_event(self, event):
        if not self.visible: return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pygame.Rect(self.x, self.y, self.width, 30).collidepoint(event.pos):
                self.dragging = True
                self.drag_offset = pygame.Vector2(event.pos) - pygame.Vector2(self.x, self.y)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            new_pos = pygame.Vector2(event.pos) - self.drag_offset
            self.x, self.y = int(new_pos.x), int(new_pos.y)
            self.sync_positions()
        if self.quit_window_button.clicked(event): 
            self.visible = False
            self.dragging = False
        if self.delete_object_button.clicked(event) and self.selected_mass in List_of_Masses:
            List_of_Masses.remove(self.selected_mass)
        if self.pin_button.clicked(event) and self.selected_mass:
            self.selected_mass.pinned = not self.selected_mass.pinned
        
        boxes = [self.mass_box, self.pos_x_box, self.pos_y_box, self.vel_x_box, self.vel_y_box]
        for box in boxes: box.handle_event(event)
        if self.selected_mass:
            try:
                if self.mass_box.submitted():
                    self.selected_mass.mass = max(1, float(self.mass_box.get_text()))
                    self.selected_mass.radius = int(self.selected_mass.mass ** (1/3))
                if self.pos_x_box.submitted(): self.selected_mass.position.x = float(self.pos_x_box.get_text())
                if self.pos_y_box.submitted(): self.selected_mass.position.y = float(self.pos_y_box.get_text())
                if self.vel_x_box.submitted(): self.selected_mass.velocity.x = float(self.vel_x_box.get_text())
                if self.vel_y_box.submitted(): self.selected_mass.velocity.y = float(self.vel_y_box.get_text())
            except ValueError: pass

    def draw(self, screen):
        if not self.visible or not self.selected_mass or self.selected_mass not in List_of_Masses:
            self.visible = False
            return
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, (40,40,60), panel_rect, border_radius=10)
        pygame.draw.rect(screen, (200,200,255), panel_rect, 2, border_radius=10)
        pygame.draw.rect(screen, (60,60,90), pygame.Rect(self.x, self.y, self.width, 30), border_radius=10)
        font = pygame.font.Font(None, 24)
        screen.blit(font.render(f"Inspector: Mass {List_of_Masses.index(self.selected_mass)}", True, (255,255,255)), (self.x+10, self.y+5))
        labels = [("Edit Mass:", self.y+40), ("Pos X:", self.y+100), ("Pos Y:", self.y+150), ("Vel X:", self.y+210), ("Vel Y:", self.y+260)]
        for text, y_pos in labels: screen.blit(font.render(text, True, (255,255,255)), (self.x+20, y_pos))
        
        if not self.mass_box.active: self.mass_box.text = str(round(self.selected_mass.mass, 1))
        if not self.pos_x_box.active: self.pos_x_box.text = str(round(self.selected_mass.position.x, 2))
        if not self.pos_y_box.active: self.pos_y_box.text = str(round(self.selected_mass.position.y, 2))
        if not self.vel_x_box.active: self.vel_x_box.text = str(round(self.selected_mass.velocity.x, 2))
        if not self.vel_y_box.active: self.vel_y_box.text = str(round(self.selected_mass.velocity.y, 2))

        for box in [self.mass_box, self.pos_x_box, self.pos_y_box, self.vel_x_box, self.vel_y_box]:
            box.text_surface = box.font.render(box.text, True, box.text_color)
            box.update()
            box.draw(screen)
        self.pin_button.text = "Unpin Mass" if self.selected_mass.pinned else "Pin Mass"
        self.pin_button.draw()
        self.quit_window_button.draw()
        self.delete_object_button.draw()

    def is_clicked(self, pos): return self.visible and pygame.Rect(self.x, self.y, self.width, self.height).collidepoint(pos)

#Draws the title
def draw_title_plate(text, cx, cy, px=20, py=10):
    title_font = pygame.font.SysFont("arial", 64, bold=True)
    text_surf = title_font.render(text, True, (255,255,255))
    plate_rect = text_surf.get_rect(center=(cx, cy))
    plate_rect.inflate_ip(px*2, py*2)
    pygame.draw.rect(screen, (40,40,60), plate_rect, border_radius=14)
    pygame.draw.rect(screen, (200,200,255), plate_rect, 3, border_radius=14)
    screen.blit(text_surf, text_surf.get_rect(center=plate_rect.center))

# Draws the pause /play button in the top right corner
def isPausedDrawing(isitpaused):
    color, sx, sy, size = (120, 120, 120), 750, 15, 30
    if isitpaused:
        pygame.draw.polygon(screen, color, [(sx, sy), (sx, sy + size), (sx + 25, sy + (size // 2))])
    else:
        rw, gap = 8, 8
        pygame.draw.rect(screen, color, (sx, sy, rw, size))
        pygame.draw.rect(screen, color, (sx + rw + gap, sy, rw, size))

# Draw the main menu with title and buttons
def draw_menu():
    draw_title_plate("Moji's Gravity Simulator", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.25)
    start_button.draw()
    help_button.draw()
    exit_button.draw()

#Draws the help screen with instructions
def draw_help():
    draw_title_plate("Simulator Info", SCREEN_WIDTH/2, 60)
    help_rect = pygame.Rect(50, 110, SCREEN_WIDTH - 100, 400)
    pygame.draw.rect(screen, (30, 30, 50), help_rect, border_radius=15)
    pygame.draw.rect(screen, (200, 200, 255), help_rect, 2, border_radius=15)
    font = pygame.font.Font(None, 24)
    basics = ["• LEFT CLICK + DRAG: Launch new masses", "• RIGHT CLICK MASS: Open Inspector", "• SPACE: Pause/Resume", "• TAB: Toggle Settings"]
    for i, line in enumerate(basics): screen.blit(font.render(line, True, (255, 255, 255)), (80, 130 + (i * 28)))
    advanced = ["• C: Show/Hide trails", "• V: Show/Hide velocity arrows"]
    for i, line in enumerate(advanced): screen.blit(font.render(line, True, (200, 200, 255)), (450, 130 + (i * 28)))
    pygame.draw.line(screen, (100, 100, 150), (100, 265), (SCREEN_WIDTH - 100, 265), 1)
    
    words, lines, cur = USER_BLURB.split(' '), [], ""
    for w in words:
        if font.size(cur + w + " ")[0] < (SCREEN_WIDTH - 160): cur += w + " "
        else: lines.append(cur); cur = w + " "
    lines.append(cur)
    for i, line in enumerate(lines):
        bs = font.render(line, True, (180, 180, 210))
        screen.blit(bs, bs.get_rect(center=(SCREEN_WIDTH//2, 300 + (i * 25))))
    back_button.draw()

#Draws the main sim
def draw_playing():
    for mass in List_of_Masses:
        if not PAUSE: mass.update(TIME_SCALE / FPS)
        mass.draw()
        if settings_panel.show_trails: mass.draw_trail()
        else: mass.trail.clear()
        if settings_panel.show_vectors: mass.showvelocity()
    if dragging_mass:
        pygame.draw.circle(screen, (255,255,0), drag_start, 10)
        pygame.draw.line(screen, (255,255,255), drag_start, drag_current, 2)
        pv = (drag_start - drag_current) * VELOCITY_SCALE
        pygame.draw.line(screen, (0,255,0), drag_start, drag_start + pv * 10, 2)
    isPausedDrawing(PAUSE)
    settings_panel.draw(screen)
    inspector_panel.draw(screen)

#ALL THE EVENTS FOR THE PLAYING STATE ARE HANDLED HERE
def handle_events_playing(events):
    global dragging_mass, drag_start, drag_current, GAMESTATE, PAUSE
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: GAMESTATE, PAUSE = "MENU", True
            if event.key == pygame.K_SPACE: PAUSE = not PAUSE
            if event.key == pygame.K_TAB: settings_panel.visible = not settings_panel.visible
        
        cp = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if (settings_panel.visible and settings_panel.is_clicked(event.pos)) or (inspector_panel.visible and inspector_panel.is_clicked(event.pos)): cp = True
        
        settings_panel.handle_event(event)
        inspector_panel.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not cp:
            if not any((pygame.Vector2(event.pos) - m.position).length() <= m.radius for m in List_of_Masses):
                dragging_mass, drag_start = True, pygame.Vector2(event.pos)
                drag_current = drag_start
        if event.type == pygame.MOUSEMOTION and dragging_mass: drag_current = pygame.Vector2(event.pos)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and dragging_mass:
            dragging_mass = False
            lv = (drag_start - drag_current) * VELOCITY_SCALE
            if lv.length() > MAX_LAUNCH_SPEED: lv.scale_to_length(MAX_LAUNCH_SPEED)
            List_of_Masses.append(Mass(1000, drag_start, lv, (0,0), (255,255,0)))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for mass in List_of_Masses:
                if (pygame.Vector2(event.pos) - mass.position).length() <= mass.radius:
                    inspector_panel.selected_mass, inspector_panel.visible = mass, True
                    inspector_panel.mass_box.text = str(mass.mass)
                    inspector_panel.pos_x_box.text = str(round(mass.position.x, 2))
                    inspector_panel.pos_y_box.text = str(round(mass.position.y, 2))
                    inspector_panel.vel_x_box.text = str(round(mass.velocity.x, 2))
                    inspector_panel.vel_y_box.text = str(round(mass.velocity.y, 2))
                    break

# Initialize panels and buttons
settings_panel = SettingsPanel()
inspector_panel = InspectorPanel()
start_button = Button((SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 - 75, 300, 50), "Start Simulation")
help_button = Button((SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2, 300, 50), "Help")
exit_button = Button((SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 + 75, 300, 50), "Exit")
back_button = Button((SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT - 80, 200, 50), "Back to Menu")

running = True

#Main game loop
while running:
    screen.fill((22,22,22))
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT: running = False

    if GAMESTATE == "MENU":
        for e in events:
            if start_button.clicked(e): GAMESTATE = "PLAYING"
            if help_button.clicked(e): GAMESTATE = "HELP"
            if exit_button.clicked(e): running = False
        draw_menu()
    elif GAMESTATE == "PLAYING":
        handle_events_playing(events)
        draw_playing()
    elif GAMESTATE == "HELP":
        for e in events:
            if back_button.clicked(e): GAMESTATE = "MENU"
        draw_help()

    pygame.display.flip()
    clock.tick(FPS)
#if quit it quits
pygame.quit()