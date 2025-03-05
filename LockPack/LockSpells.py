import Spells
import BossSpawns
import CommonContent
import Level, LevelGen, Game
import Monsters, RareMonsters, Variants
import Mutators
import Consumables
import Upgrades
import Equipment, Shrines
import random, os, copy, math
import mods.LockPack.LockCore as Core


class BasicLock(Level.Spell):

    def on_init(self):

        self.name = "Lock-On"
        self.asset = ["LockPack", "assets", "icons", "lock_on"]
        self.max_charges = 0
        self.range = Level.RANGE_GLOBAL
        self.tags = [Level.Tags.Locking]
        self.level = 1
        self.can_target_empty = False
        self.can_target_self = True

    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['cap'] = self.caster.lock_cap
        return d

    def get_description(self):
        return (
            "Lock on to any number of targets, up to the Wizard's [lock_cap_of_{cap}:locking]. Cast on yourself to finish targeting early.\n"
            "Cannot be cast if there are [{cap}:locking] locked units.\n"
            + Core.lock_cap_infobox + "\n" + Core.lock_infobox
            ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        for m in self.multi_targets:
            if (u := self.caster.level.get_unit_at(m.x, m.y)):
                if u != self.caster:
                    u.apply_buff(Core.Locked())

    def has_enough_targets(self):
        if any(self.caster.level.get_unit_at(t.x, t.y) == self.caster for t in self.multi_targets):
            return True
        if len(Core.get_locked(self.caster.level) + self.multi_targets) == self.caster.lock_cap:
            return True
    
    def can_pay_costs(self):
        return len(Core.get_locked(self.caster.level)) < self.caster.lock_cap
    
class SuperLockDebuff(Level.Buff):
    def on_init(self):
        self.color = Level.Tags.Locking.color
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.stack_type = Level.STACK_INTENSITY
        self.global_bonuses['max_charges'] = -1
        self.name = "Lock Overload"

class SuperLock(Level.Spell):

    def on_init(self):

        self.name = "Desperate Targeting"
        self.asset = ["LockPack", "assets", "icons", "desperate_lock"]
        self.max_charges = 0
        self.range = Level.RANGE_GLOBAL
        self.tags = [Level.Tags.Locking]
        self.level = 3
        self.can_target_empty = False
        self.can_target_self = True

    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['cap'] = self.caster.lock_cap
        d['max'] = d['cap']*2
        return d

    def get_description(self):
        return (
            "Lock on to any number of targets, up to [{max}:locking]. Cast on yourself to finish targeting early.\n"
            "If casting this spell causes there to be more than [{cap}_locked_units:locking], all spells and skills lose 1 max charge for each extra unit for a fixed 15 turns.\n"
            "Cannot be cast if there are [{max}:locking] locked units.\n"
            + Core.lock_infobox
            ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        for m in self.multi_targets:
            if (u := self.caster.level.get_unit_at(m.x, m.y)):
                if u != self.caster:
                    u.apply_buff(Core.Locked())
        num_over = (len(Core.get_locked(self.caster.level)) - self.caster.lock_cap)
        for _ in range(num_over):
            self.caster.apply_buff(SuperLockDebuff(), 15)

    def has_enough_targets(self):
        if any(self.caster.level.get_unit_at(t.x, t.y) == self.caster for t in self.multi_targets):
            return True
        if len(Core.get_locked(self.caster.level) + self.multi_targets) == self.caster.lock_cap*2:
            return True
    
    def can_pay_costs(self):
        return len(Core.get_locked(self.caster.level)) < self.caster.lock_cap*2
    

class Hypnotize(Level.Spell):

    def on_init(self):

        self.name = "Selective Suggestion"
        self.asset = ["LockPack", "assets", "icons", "suggestion"]
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Locking, Level.Tags.Arcane, Level.Tags.Enchantment]
        self.level = 4
        self.duration = 2

        self.upgrades['duration'] = (3, 2)
        self.upgrades['beam'] = (1, 4, "Rage Beam", "Affected units cast Void Beam instead.")

    def get_description(self):
        return (
            "Each [locked:locking] unit goes [berserk] for [{duration}_turns:duration], then casts your Magic Missile on a random valid target."
            ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        for v in Core.get_locked(self.caster.level):
            v.apply_buff(Level.BerserkBuff(), self.get_stat('duration'))
            s = self.caster.get_or_make_spell(Spells.MagicMissile if not self.get_stat('beam') else Spells.VoidBeamSpell)
            s.owner = s.caster = v
            potentials = [u for u in self.caster.level.units if s.can_cast(u.x, u.y)]
            if not potentials:
                continue
            tgt = random.choice(potentials)
            self.caster.level.act_cast(v, s, tgt.x, tgt.y, pay_costs=False)

class DieOnMove(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.color = Level.Tags.Translocation.color
        self.owner_triggers[Level.EventOnMoved] = self.check_dist

    def check_dist(self, evt):
        b = self.owner.get_buff(CommonContent.DeathExplosion)
        if not b:
            return
        if any(Level.distance(self.owner, u) <= b.radius for u in Core.get_locked(self.owner.level)):
            self.owner.kill()
            pass
    
    def get_tooltip(self):
        return "Automatically explodes if a [locked:locking] unit is in range."
    
    def on_advance(self):
        if self.owner.is_alive():
            self.check_dist(None)

class GenericHasteBuff(Level.Buff):
    def __init__(self, power):
        Level.Buff.__init__(self)
        self.name = "Haste %d" % power
        self.power = power
        self.color = Level.Tags.Holy.color
        self.buff_type = Level.BUFF_TYPE_BLESS

    def on_advance(self):
        for i in range(self.power):
            if self.owner and self.owner.is_alive():
                self.owner.level.leap_effect(self.owner.x, self.owner.y, random.choice([t.color for t in self.owner.tags]), self.owner)
                self.owner.advance()
    
    def get_tooltip(self):
        return "Takes %d extra actions each turn" % self.power
        
class Spiderbots(Level.Spell):

    def on_init(self):

        self.name = "Clockwork Spider"
        self.asset = ["LockPack", "assets", "icons", "spiderbot"]
        self.max_charges = 5
        self.range = 0
        self.tags = [Level.Tags.Locking, Level.Tags.Metallic, Level.Tags.Conjuration]
        self.level = 3
        self.duration = 2
        self.minion_health = 16
        self.minion_damage = 13
        self.radius = 3

        self.upgrades['tanks'] = (1, 6, "Spider Tanks", "Summon spider tanks instead.")
        self.upgrades['double'] = (1, 3, "Redundancy", "Clockwork spiders reincarnate one time on death.")
        self.upgrades['radius'] = (3, 4, "Double Payload")

    def get_description(self):
        return (
            "Summon a clockwork spider next to each [locked:locking] unit."
            ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        s = [self.spider()] + self.spell_upgrades
        s.insert(2, self.tank())
        return s
    
    def spider(self):
        s = Level.Unit()
        s.max_hp = self.get_stat('minion_health')
        s.tags = [Level.Tags.Metallic, Level.Tags.Construct, Level.Tags.Spider]
        s.asset = ["LockPack", "assets", "units", "spiderbot"]
        s.buffs = [DieOnMove(), CommonContent.DeathExplosion(self.get_stat('minion_damage'), self.get_stat('radius'), Level.Tags.Physical)]
        s.name = "Clockwork Spider"
        if self.get_stat('double'):
            s.buffs += [CommonContent.ReincarnationBuff(1)]
        return s
    
    def tank(self):
        s = Level.Unit()
        s.max_hp = self.get_stat('minion_health')*3
        s.tags = [Level.Tags.Metallic, Level.Tags.Construct, Level.Tags.Spider]
        s.asset = ["LockPack", "assets", "units", "spiderbot"]
        s.name = "Spider Tank"
        turret = CommonContent.SimpleRangedAttack(damage=self.get_stat('minion_damage')//2, damage_type=Level.Tags.Physical, name="Arachnoturret")
        def drain(self, target):
            self.max_hp += 1
            self.cur_hp += 1
            CommonContent.drain_max_hp(target, 1)
        bomb = CommonContent.SimpleBurst(damage=self.get_stat('minion_damage'), radius=self.get_stat('radius'), damage_type=Level.Tags.Fire, cool_down=5, ignore_walls=True, onhit=drain, extra_desc="Drains 1 max hp from hit targets")
        bomb.name = "Wither Bomb"
        s.buffs = [GenericHasteBuff(2)]
        s.spells = [bomb, turret]
        return s
    
    def cast_instant(self, x, y):
        for v in Core.get_locked(self.caster.level):
            u = self.spider()
            if self.get_stat('tanks'):
                u = self.tank()
            self.summon(u, v)
            

Spells.all_player_spell_constructors.extend([BasicLock, SuperLock, Hypnotize, Spiderbots])