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

class HellUnite(Upgrades.Upgrade):

    def on_init(self):
        self.name = "Fiendish Unity"
        self.tags = [Level.Tags.Dark, Level.Tags.Chaos]
        self.level = 7
        self.description = "[Undead] minions gain [demon] and vice versa.\nHas no effect on units with both tags."
        self.global_triggers[Level.EventOnUnitAdded] = self.on_unit_add
        self.asset = ["ATGMPack", "icons", "hell_unity"]

    def on_unit_add(self, evt):
        if Level.are_hostile(evt.unit, self.owner):
            return
        elif Level.Tags.Demon in evt.unit.tags and Level.Tags.Undead not in evt.unit.tags:
            evt.unit.tags.append(Level.Tags.Undead)
        elif Level.Tags.Undead in evt.unit.tags and Level.Tags.Demon not in evt.unit.tags:
            evt.unit.tags.append(Level.Tags.Demon)

class Deathdeal(Upgrades.Upgrade):

    def on_init(self):
        self.scale_ct = 1
        self.num_dead = self.dmg = 0
        self.name = "Requiem for the Lost"
        self.tags = [Level.Tags.Dark]
        self.level = 6
        self.global_triggers[Level.EventOnDeath] = self.scale
        self.asset = ["ATGMPack", "icons", "requiem"]

    def get_description(self):
        return f"Deal [dark] damage to the nearest enemy each turn based on the number of allies that have died since learning this skill, with diminishing returns. Only deaths in active realms are counted.\nCurrently deals [{self.dmg}_damage:damage]."
    
    def scale(self, evt):
        if not Level.are_hostile(evt.unit, self.owner) and any(Level.are_hostile(u, self.owner) for u in self.owner.level.units):
            self.num_dead += 1
            if self.num_dead == self.scale_ct:
                self.scale_ct += 1
                self.dmg += 1
                self.num_dead = 0
    
    def on_advance(self):
        options = [u for u in self.owner.level.units if Level.are_hostile(u, self.owner)]
        random.shuffle(options)
        if not options or not self.dmg:
            return
        options.sort(key=lambda u: Level.distance(u, self.owner))
        options[0].deal_damage(self.dmg, Level.Tags.Dark, self)

class StarBoon(Level.Buff):
    def __init__(self, val):
        Level.Buff.__init__(self)
        self.val = val
        self.name = "Boon of the Stars"
        self.color = Level.Tags.Holy.color
        self.buff_type = Level.BUFF_TYPE_BLESS
    
    def on_advance(self):
        self.owner.max_hp += self.val
        self.owner.cur_hp += self.val

class Starfriend(Upgrades.Upgrade):
    
    def on_init(self):
        self.name = "Starfriends"
        self.tags = [Level.Tags.Arcane, Level.Tags.Holy, Level.Tags.Conjuration]
        self.level = 6
        self.asset = ["ATGMPack", "icons", "starslime"]
        self.owner_triggers[Level.EventOnSpellCast] = self.proc
        self.lv_ct = 0
        self.minion_health = 10
        self.minion_damage = 3

    def get_description(self):
        return (
            "For every 15 levels of [arcane] or [holy] spells you cast, summon a starlight slime next to you.\n"
            "Its HP is rounded up to the nearest multiple of 10 on summon.\n"
            f"Current levels cast: [{self.lv_ct}:arcane]"
        )

    def proc(self, evt):
        if Level.Tags.Arcane in evt.spell.tags or Level.Tags.Holy in evt.spell.tags:
            self.lv_ct += evt.spell.level
        while self.lv_ct >= 15:
            self.summon(self.slime(), self.owner)
            self.lv_ct -= 15

    def slime(self):
        mod = math.ceil(self.get_stat('minion_health')/10)
        slime = Monsters.GreenSlime()
        slime.name = "Starlight Slime"
        slime.shields = 1
        slime.tags = [Level.Tags.Arcane, Level.Tags.Holy, Level.Tags.Slime]
        slime.asset = ["ATGMPack", "units", "starslime"]
        boost = CommonContent.WizardSelfBuff(lambda: StarBoon(mod), 8, cool_down=10)
        boost.get_ai_target = lambda: slime if not slime.has_buff(StarBoon) else None 
        strike = CommonContent.SimpleRangedAttack(damage=3, damage_type=[Level.Tags.Arcane, Level.Tags.Holy], range=4)
        strike.name = "Starstrike"
        slime.buffs[0].spawner = self.slime
        slime.spells = [boost, strike]
        slime.resists[Level.Tags.Holy] = 100
        slime.resists[Level.Tags.Arcane] = 50
        slime.buffs.append(CommonContent.RetaliationBuff(1, Level.Tags.Holy))
        CommonContent.apply_minion_bonuses(self, slime)
        slime.max_hp = mod*10
        return slime

    def get_extra_examine_tooltips(self):
        return [self.slime()]
    
class MasterChannel(Upgrades.Upgrade):
    
    def on_init(self):
        self.name = "Master Channel"
        self.tags = [Level.Tags.Arcane]
        self.level = 5
        self.asset = ["ATGMPack", "icons", "master_channel"]
        self.global_bonuses['max_channel'] = 4

class Deadlord(Upgrades.Upgrade):
    
    def on_init(self):
        self.name = "Nefarious Bargain"
        self.tags = [Level.Tags.Dark]
        self.level = 8
        self.asset = ["ATGMPack", "icons", "necrotize"]
        self.resists[Level.Tags.Holy] = -100
        self.resists[Level.Tags.Poison] = 100
        self.resists[Level.Tags.Ice] = 50
        self.resists[Level.Tags.Dark] = 100
        self.description = "Gain [undead] when purchasing this skill.\nThis change is permanent."

    def on_applied(self, owner):
        if Level.Tags.Undead not in owner.tags:
            owner.tags.append(Level.Tags.Undead)

    def on_unapplied(self):
        self.owner.tags = [t for t in self.owner.tags if t != Level.Tags.Undead]

class OrbPonderanceBuff(Level.Buff):

    def __init__(self):
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.advfunction = None
        self.color = Level.Tags.Orb.color
        self.name = "Pondered Orb"
    
    def on_applied(self, owner):
        o = self.owner.get_buff(Spells.OrbBuff)
        self.advfunction = o.on_advance
        o.on_advance = lambda: o.spell.on_orb_move(self.owner, self.owner)
    
    def on_attempt_advance(self):
        self.owner.turns_to_death += 1
        return False
    
    def on_unapplied(self):
        o = self.owner.get_buff(Spells.OrbBuff)
        o.on_advance = self.advfunction
        

class OrbPonder2(Upgrades.Upgrade):
    
    def on_init(self):
        self.name = "Ponderance"
        self.tags = [Level.Tags.Orb]
        self.level = 5
        self.owner_triggers[Level.EventOnPass] = self.proc
        self.duration = 1
        self.asset = ["ATGMPack", "icons", "ponderance"]

    def get_description(self):
        return (
            "When you pass your turn without moving or casting a spell, a random [orb] minion gains Pondered for [{duration}_turns:duration].\n"
            "An orb that has Pondered cannot act, but it does not lose duration or the ability to activate its per-turn effect."
        ).format(**self.fmt_dict())
    
    def proc(self, evt):
        orbs = [u for u in self.owner.level.units if isinstance(u.source, Spells.OrbSpell) and not Level.are_hostile(u, self.owner)]
        if not orbs:
            return
        orb = random.choice(orbs)
        orb.apply_buff(OrbPonderanceBuff(), self.get_stat('duration'))


class MasterSnipe(Upgrades.Upgrade):
    
    def on_init(self):
        self.name = "Minion Lens"
        self.tags = [Level.Tags.Arcane]
        self.level = 5
        self.asset = ["ATGMPack", "icons", "conjured_sniper"]
        self.global_bonuses['minion_range'] = 1

class Nearsight(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Nearsightedness"
        self.tags = [Level.Tags.Eye, Level.Tags.Arcane]
        self.level = 5
        self.asset = ["ATGMPack", "icons", "nearsight"]
        self.damage = 13
        self.global_triggers[Level.EventOnDamaged] = self.proc
    
    def get_description(self):
        return (
            "Whenever an enemy takes damage from an eye spell, if you are less than 8 tiles away, deal [{damage}_arcane_damage:arcane] to them."
        ).format(**self.fmt_dict())
    
    def proc(self, evt):
        print(type(evt.source))
        if not Level.are_hostile(evt.unit, self.owner):
            return
        if not isinstance(evt.source, Level.Spell) or Level.Tags.Eye not in evt.source.tags:
            return
        if Level.distance(evt.unit, self.owner) > 8:
            return
        evt.unit.deal_damage(self.damage, Level.Tags.Arcane, self)


class ArchSigil(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Bloodiron Sigil"
        self.tags = [Level.Tags.Blood, Level.Tags.Metallic]
        self.level = 6
        self.asset = ["ATGMPack", "icons", "runic_master"]
        self.minion_health = 20
        self.global_triggers[Level.EventOnUnitAdded] = self.proc
    
    def get_description(self):
        return (
            "Spawners from sigils have the [metallic] modifier applied directly to them and gain [{minion_health}_HP:minion_health].\n"
            "However, you lose 4 HP whenever you summon a spawner from a sigil. This damage can kill you."
        ).format(**self.fmt_dict())
    
    def proc(self, evt):
        if type(evt.unit.source) != Equipment.PetSigil or Level.are_hostile(self.owner, evt.unit):
            return
        BossSpawns.apply_modifier(BossSpawns.Metallic, evt.unit)
        evt.unit.max_hp += self.get_stat('minion_health')
        evt.unit.cur_hp = evt.unit.max_hp
        self.owner.cur_hp = max(self.owner.cur_hp-4, 0)
        if self.owner.cur_hp <= 0:
            self.owner.kill()

class GobPunch(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Goblin Punch"
        self.tags = [Level.Tags.Nature, Level.Tags.Sorcery]
        self.level = 3
        self.damage = 5
        self.asset = ["ATGMPack", "icons", "gobpunch"]

    def fmt_dict(self):
        d = Upgrades.Upgrade.fmt_dict(self)
        d['multiplied'] = 5*d['damage']
        return d
    
    def get_description(self):
        return (
            "Each turn, deal [{damage}_physical_damage:physical] to one enemy in melee range.\n"
            "If your HP and the enemy's HP differ by no more than [{damage}:damage], deal [{multiplied}_damage:damage] instead."
        ).format(**self.fmt_dict())
    
    def on_advance(self):
        candidates = [u for u in self.owner.level.get_units_in_ball(self.owner, 1, diag=True) if Level.are_hostile(self.owner, u)]
        if not candidates:
            return
        v = random.choice(candidates)
        dmg = self.get_stat('damage')
        diff = abs(v.cur_hp - self.owner.cur_hp)
        if diff <= self.get_stat('damage'):
            dmg *= 5
        v.deal_damage(dmg, Level.Tags.Physical, self)


mod_skills = [
    HellUnite,
    Deathdeal,
    Starfriend,
    MasterChannel,
    Deadlord,
    OrbPonder2,
    MasterSnipe,
    Nearsight,
    ArchSigil,
    GobPunch
]
     

Upgrades.skill_constructors.extend(mod_skills)