import arcade
import math
import random
import sqlite3


SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
SCREEN_TITLE = "айзек"

PLAYER_SPEED = 5
ANIMATION_SPEED = 0.15
BORDER = 100

BULLET_SPEED = 7
BULLET_SCALE = 0.7
BULLET_RANGE = 400
SHOOT_DELAY = 0.5

MAP_LEFT = 100
MAP_RIGHT = SCREEN_WIDTH - 100
MAP_BOTTOM = 100
MAP_TOP = SCREEN_HEIGHT - 50

PLAYER_MAX_HP = 3
ENEMY_MAX_HP = 3
PEAR_ACTIVE_TIME = 5.0
PEAR_REST_TIME = 2.0
PEAR_MOVE_DELAY = 0.7


class PearEnemy(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__("images/grusha.png", scale=0.5)

        self.center_x = x
        self.center_y = y

        self.hp = ENEMY_MAX_HP
        self.state = "active"

        self.state_timer = 0
        self.move_timer = 0
        self.hit_timer = 0

        self.base_scale = 0.5
        self.scale = self.base_scale

    def update(self, delta_time):
        self.state_timer += delta_time
        self.move_timer += delta_time

        if self.state == "active":
            if self.move_timer >= PEAR_MOVE_DELAY:
                self.move_timer = 0
                self.random_move()

            if self.state_timer >= PEAR_ACTIVE_TIME:
                self.state = "rest"
                self.state_timer = 0
                self.move_timer = 0

        elif self.state == "rest":
            if self.state_timer >= PEAR_REST_TIME:
                self.state = "active"
                self.state_timer = 0

        if self.hit_timer > 0:
            self.hit_timer -= delta_time
            self.color = arcade.color.RED_ORANGE
            self.alpha = 180
            self.center_x += random.randint(-2, 2)
            self.center_y += random.randint(-2, 2)
        else:
            self.color = arcade.color.WHITE
            self.alpha = 255

        if self.move_timer > PEAR_MOVE_DELAY - 0.3:
            self.center_x += random.randint(-2, 2)
            self.center_y += random.randint(-2, 2)

        if self.state == "active":
            self.scale = 0.5 + math.sin(self.state_timer * 6) * 0.05
        else:
            self.scale = 0.5

    def random_move(self):
        self.center_x = random.randint(MAP_LEFT + 30, MAP_RIGHT - 30)
        self.center_y = random.randint(MAP_BOTTOM + 30, MAP_TOP - 30)


class Collider(arcade.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()

        self.texture = arcade.make_soft_square_texture(
            1, arcade.color.WHITE, 0, 0
        )

        self.scale_x = width
        self.scale_y = height

        self.center_x = x
        self.center_y = y


class StartView(arcade.View):
    def __init__(self):
        super().__init__()

        self.background = arcade.load_texture("images/start.jpg")

        self.start_area = arcade.rect.XYWH(
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT * 0.2,
            200,
            50
        )

    def on_draw(self):
        self.clear()

        arcade.draw_texture_rect(
            self.background,
            arcade.rect.XYWH(
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 2,
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            )
        )

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            game_view = GameView()
            game_view.setup()
            self.window.show_view(game_view)

    def on_mouse_press(self, x, y, button, modifiers):
        left = self.start_area.x - self.start_area.width / 2
        right = self.start_area.x + self.start_area.width / 2
        bottom = self.start_area.y - self.start_area.height / 2
        top = self.start_area.y + self.start_area.height / 2

        if left <= x <= right and bottom <= y <= top:
            game_view = GameView()
            game_view.setup()
            self.window.show_view(game_view)


class Particle(arcade.Sprite):
    def __init__(self, x, y, textures):
        super().__init__(textures[0], scale=1.0)

        self.center_x = x
        self.center_y = y

        self.textures = textures
        self.frame = 0
        self.timer = 0
        self.frame_time = 0.05

    def update(self, delta_time: float = 1/60):
        self.timer += delta_time

        if self.timer >= self.frame_time:
            self.timer = 0
            self.frame += 1

            if self.frame >= len(self.textures):
                self.remove_from_sprite_lists()
                return

            self.texture = self.textures[self.frame]


class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.physics_engine = None

        self.player_list = None
        self.bullet_list = None
        self.player = None

        self.up = self.down = self.left = self.right = False
        self.shoot_up = self.shoot_down = False
        self.shoot_left = self.shoot_right = False

        self.facing = "down"

        self.idle_texture = None
        self.walk_textures = {}

        self.current_frame = 0
        self.animation_timer = 0

        self.shoot_cooldown = 0
        self.particles = arcade.SpriteList()
        self.particle_textures = []

        self.maps = {
            "first": arcade.load_texture("images/firstmap.jpg"),
            "second": arcade.load_texture("images/secondmap.jpg"),
            "third": arcade.load_texture("images/thirdmap.jpg"),
        }

        self.current_map = "first"
        self.right_door = arcade.rect.XYWH(
            SCREEN_WIDTH - 60,
            SCREEN_HEIGHT // 2,
            80,
            160
        )

        self.top_door = arcade.rect.XYWH(
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 60,
            160,
            80
        )

        self.left_door = arcade.rect.XYWH(
            60,
            SCREEN_HEIGHT // 2,
            80,
            160
        )

        self.bottom_door = arcade.rect.XYWH(
            SCREEN_WIDTH // 2,
            60,
            160,
            80
        )
        self.room_transition_cooldown = 0

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()

        self.idle_texture = arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918.png")
        self.walk_textures = {
            "down": [
                arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918 (1).png"),
                arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918 (2).png"),
            ],
            "up": [
                arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918 (7).png"),
                arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918 (8).png"),
            ],
            "left": [
                arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918 (3).png"),
                arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918 (4).png"),
            ],
            "right": [
                arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918 (5).png"),
                arcade.load_texture("images/6f5a2da7e8e897eb91dd2771070e6918 (6).png"),
            ],
        }
        self.particle_textures = [
            arcade.load_texture("images/chastitsa.png"),
            arcade.load_texture("images/chastitsa(1).png"),
            arcade.load_texture("images/chastitsa(2).png"),
            arcade.load_texture("images/chastitsa(3).png"),
            arcade.load_texture("images/chastitsa(4).png"),
            arcade.load_texture("images/chastitsa(5).png"),
            arcade.load_texture("images/chastitsa(6).png"),
        ]
        self.player = arcade.Sprite()
        self.player.texture = self.idle_texture
        self.player.scale = 2
        self.player.center_x = SCREEN_WIDTH // 2
        self.player.center_y = SCREEN_HEIGHT // 2
        self.player_list.append(self.player)
        self.enemies = arcade.SpriteList()
        self.load_colliders()
        self.physics_engine = arcade.PhysicsEngineSimple(
            self.player,
            self.wall_list
        )
        self.player_hp = PLAYER_MAX_HP
        self.spawn_enemies_for_room()
        self.db_conn = sqlite3.connect("DatabaseIsaac.sqlite")
        self.db_cursor = self.db_conn.cursor()

        self.killed_pears = 0
        self.game_finished = False

    def on_draw(self):
        self.clear()

        arcade.draw_texture_rect(
            self.maps[self.current_map],
            arcade.rect.XYWH(
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 2,
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            )
        )

        self.player_list.draw()
        self.bullet_list.draw()
        self.particles.draw()
        self.draw_hud()
        self.enemies.draw()

    def on_update(self, delta_time):
        if self.game_finished:
            return

        self.player.change_x = 0
        self.player.change_y = 0

        moving = False

        if self.up:
            self.player.change_y = PLAYER_SPEED
            self.facing = "up"
            moving = True
        elif self.down:
            self.player.change_y = -PLAYER_SPEED
            self.facing = "down"
            moving = True
        elif self.left:
            self.player.change_x = -PLAYER_SPEED
            self.facing = "left"
            moving = True
        elif self.right:
            self.player.change_x = PLAYER_SPEED
            self.facing = "right"
            moving = True

        if moving:
            self.animation_timer += delta_time
            if self.animation_timer >= ANIMATION_SPEED:
                self.animation_timer = 0
                frames = self.walk_textures[self.facing]
                self.current_frame = (self.current_frame + 1) % len(frames)
                self.player.texture = frames[self.current_frame]
        else:
            self.player.texture = self.idle_texture
            self.current_frame = 0
            self.animation_timer = 0

        self.physics_engine.update()

        self.player.center_x = max(BORDER, min(self.player.center_x, SCREEN_WIDTH - BORDER))
        self.player.center_y = max(BORDER, min(self.player.center_y, SCREEN_HEIGHT - BORDER))

        self.shoot_cooldown += delta_time

        if self.shoot_cooldown >= SHOOT_DELAY:
            if self.shoot_up:
                self.shoot("up")
            elif self.shoot_down:
                self.shoot("down")
            elif self.shoot_left:
                self.shoot("left")
            elif self.shoot_right:
                self.shoot("right")

        self.bullet_list.update()

        margin = 100

        for bullet in list(self.bullet_list):
            distance = math.dist(
                (bullet.start_x, bullet.start_y),
                (bullet.center_x, bullet.center_y)
            )

            out_of_screen = (
                    bullet.center_x < 0
                    or bullet.center_x > SCREEN_WIDTH
                    or bullet.center_y < 0
                    or bullet.center_y > SCREEN_HEIGHT
            )

            if distance >= BULLET_RANGE or out_of_screen:
                near_wall = (
                        bullet.center_x < margin
                        or bullet.center_x > SCREEN_WIDTH - margin
                        or bullet.center_y < margin
                        or bullet.center_y > SCREEN_HEIGHT - margin
                )

                self.spawn_explosion(
                    bullet.center_x,
                    bullet.center_y,
                    strong=near_wall
                )

                bullet.remove_from_sprite_lists()

        if self.room_transition_cooldown > 0:
            self.room_transition_cooldown -= delta_time

        if self.room_transition_cooldown <= 0:
            px = self.player.center_x
            py = self.player.center_y
            if self.current_map == "first":
                if self._in_rect(px, py, self.right_door):
                    self.current_map = "second"
                    self.player.center_x = MAP_LEFT + 40
                    self.player.center_y = SCREEN_HEIGHT // 2
                    self.load_colliders()
                    self.physics_engine = arcade.PhysicsEngineSimple(
                        self.player,
                        self.wall_list
                    )
                    self.spawn_enemies_for_room()
                    self.room_transition_cooldown = 0.4

                elif self._in_rect(px, py, self.top_door):
                    self.current_map = "third"
                    self.player.center_x = SCREEN_WIDTH // 2
                    self.player.center_y = MAP_BOTTOM + 40
                    self.load_colliders()
                    self.physics_engine = arcade.PhysicsEngineSimple(
                        self.player,
                        self.wall_list
                    )
                    self.spawn_enemies_for_room()
                    self.room_transition_cooldown = 0.4

            elif self.current_map == "second":
                if self._in_rect(px, py, self.left_door):
                    self.current_map = "first"
                    self.player.center_x = MAP_RIGHT - 40
                    self.player.center_y = SCREEN_HEIGHT // 2
                    self.load_colliders()
                    self.physics_engine = arcade.PhysicsEngineSimple(
                        self.player,
                        self.wall_list
                    )
                    self.spawn_enemies_for_room()
                    self.room_transition_cooldown = 0.4

            elif self.current_map == "third":
                if self._in_rect(px, py, self.bottom_door):
                    self.current_map = "first"
                    self.player.center_x = SCREEN_WIDTH // 2
                    self.player.center_y = MAP_TOP - 40
                    self.load_colliders()
                    self.physics_engine = arcade.PhysicsEngineSimple(
                        self.player,
                        self.wall_list
                    )
                    self.spawn_enemies_for_room()
                    self.room_transition_cooldown = 0.4

        for bullet in self.bullet_list:
            hit_wall = False
            strong = False

            if bullet.center_x <= MAP_LEFT:
                bullet.center_x = MAP_LEFT
                hit_wall = True
                strong = True

            elif bullet.center_x >= MAP_RIGHT:
                bullet.center_x = MAP_RIGHT
                hit_wall = True
                strong = True

            elif bullet.center_y <= MAP_BOTTOM:
                bullet.center_y = MAP_BOTTOM
                hit_wall = True
                strong = True

            elif bullet.center_y >= MAP_TOP:
                bullet.center_y = MAP_TOP
                hit_wall = True
                strong = True

            if hit_wall:
                self.spawn_explosion(bullet.center_x, bullet.center_y, strong=strong)
                bullet.remove_from_sprite_lists()

        self.particles.update()

        for bullet in list(self.bullet_list):
            hit_list = arcade.check_for_collision_with_list(bullet, self.wall_list)
            if hit_list:
                self.spawn_explosion(bullet.center_x, bullet.center_y, strong=True)
                bullet.remove_from_sprite_lists()

        self.enemies.update(delta_time)
        for pear in self.enemies:
            if pear.state == "active":
                if arcade.check_for_collision(self.player, pear):
                    self.player_hp -= 1
                    print("Игрок получил урон")

                    pear.state = "rest"
                    pear.state_timer = 0

                    if self.player_hp <= 0 and not self.game_finished:
                        self.game_finished = True
                        self.save_result_to_db("lose", "pear")
                        self.game_over()

        for bullet in list(self.bullet_list):
            hit_list = arcade.check_for_collision_with_list(bullet, self.enemies)
            for pear in hit_list:
                pear.hp -= 1
                pear.hit_timer = 0.3
                bullet.remove_from_sprite_lists()

                if pear.hp <= 0:
                    pear.remove_from_sprite_lists()
                    self.killed_pears += 1

                    if self.killed_pears >= 2 and not self.game_finished:
                        self.game_finished = True
                        self.save_result_to_db("win", "player")
                        self.game_over()

    def shoot(self, direction):
        bullet = arcade.Sprite("images/bullet.png", scale=BULLET_SCALE)
        bullet.center_x = self.player.center_x
        bullet.center_y = self.player.center_y

        bullet.start_x = bullet.center_x
        bullet.start_y = bullet.center_y

        if direction == "up":
            bullet.change_y = BULLET_SPEED
        elif direction == "down":
            bullet.change_y = -BULLET_SPEED
        elif direction == "left":
            bullet.change_x = -BULLET_SPEED
        elif direction == "right":
            bullet.change_x = BULLET_SPEED

        self.bullet_list.append(bullet)
        self.shoot_cooldown = 0

    def on_key_press(self, key, modifiers):
        if key == arcade.key.W:
            self.up = True
        elif key == arcade.key.S:
            self.down = True
        elif key == arcade.key.A:
            self.left = True
        elif key == arcade.key.D:
            self.right = True
        elif key == arcade.key.UP:
            self.shoot_up = True
        elif key == arcade.key.DOWN:
            self.shoot_down = True
        elif key == arcade.key.LEFT:
            self.shoot_left = True
        elif key == arcade.key.RIGHT:
            self.shoot_right = True

    def on_key_release(self, key, modifiers):
        if key == arcade.key.W:
            self.up = False
        elif key == arcade.key.S:
            self.down = False
        elif key == arcade.key.A:
            self.left = False
        elif key == arcade.key.D:
            self.right = False
        elif key == arcade.key.UP:
            self.shoot_up = False
        elif key == arcade.key.DOWN:
            self.shoot_down = False
        elif key == arcade.key.LEFT:
            self.shoot_left = False
        elif key == arcade.key.RIGHT:
            self.shoot_right = False

    def spawn_explosion(self, x, y, strong=False):
        particle = Particle(x, y, self.particle_textures)

        if strong:
            particle.scale = 2.4
        else:
            particle.scale = 1.4

        self.particles.append(particle)

    def _in_rect(self, x, y, rect):
        left = rect.x - rect.width / 2
        right = rect.x + rect.width / 2
        bottom = rect.y - rect.height / 2
        top = rect.y + rect.height / 2

        return left <= x <= right and bottom <= y <= top

    def load_colliders(self):
        self.wall_list.clear()

        if self.current_map == "second":
            self.wall_list.append(Collider(430, 230, 55, 55))
            self.wall_list.append(Collider(430, 370, 55, 55))
            self.wall_list.append(Collider(570, 370, 55, 55))
            self.wall_list.append(Collider(570, 230, 55, 55))

        elif self.current_map == "third":
            self.wall_list.append(Collider(125, 125, 60, 60))
            self.wall_list.append(Collider(125, SCREEN_HEIGHT - 160, 60, 60))
            self.wall_list.append(Collider(180, SCREEN_HEIGHT - 80, 60, 60))
            self.wall_list.append(Collider(SCREEN_WIDTH - 125, SCREEN_HEIGHT - 125, 60, 60))
            self.wall_list.append(Collider(SCREEN_WIDTH - 125, 180, 60, 60))
            self.wall_list.append(Collider(SCREEN_WIDTH - 185, 105, 60, 60))

    def draw_hud(self):
        arcade.draw_text(
            f"HP: {self.player_hp}",
            12, 12,
            arcade.color.BLACK,
            22,
            bold=True
        )
        arcade.draw_text(
            f"HP: {self.player_hp}",
            10, 10,
            arcade.color.RED,
            22,
            bold=True
        )

    def save_result_to_db(self, result, who_kill):
        self.db_cursor.execute(
            "INSERT INTO Data (result, who_kill) VALUES (?, ?)",
            (result, who_kill)
        )
        self.db_conn.commit()

    def game_over(self):
        print("GAME OVER")
        self.db_conn.close()
        arcade.close_window()

    def spawn_enemies_for_room(self):
        self.enemies.clear()
        if self.current_map != "first":
            pear = PearEnemy(
                random.randint(MAP_LEFT + 40, MAP_RIGHT - 40),
                random.randint(MAP_BOTTOM + 40, MAP_TOP - 40)
            )
            self.enemies.append(pear)


def main():
    game = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    game.show_view(StartView())
    arcade.run()


if __name__ == "__main__":
    main()
