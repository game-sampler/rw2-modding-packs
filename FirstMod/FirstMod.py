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

#new spells

class SiegeQuake(Level.Buff):
    def on_init(self):
        self.name = "???"
        self.color = Level.Tags.Physical.color

    def get_tooltip(self):
        return "Emits seismic waves, turning chasms and walls into floors at a 50% rate."  

    def on_advance(self):
        ball = [p for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, 4)]
        for p in ball:
            if (self.owner.level.tiles[p.x][p.y].is_wall() or self.owner.level.tiles[p.x][p.y].is_chasm) and random.random() < .5:
                self.owner.level.make_floor(p.x, p.y)

class SiegeEngine(Level.Spell):

    def on_init(self):

        self.name = "Siege Spider"
        self.max_charges = 1
        self.range = 9
        self.tags = [Level.Tags.Conjuration, Level.Tags.Metallic]   
        self.level = 7
        self.minion_health = 21
        self.minion_damage = 28

        #self.upgrades['minion_health'] = (10, 3)
        self.upgrades['ally'] = (1, 7, "Ally Hangar", "The siege walker can cast your lowest level [conjuration] spell that is level 4 or lower on a 13 turn cooldown.\nThe walker can cast these spells with all of your upgrades and bonuses.\nThe walker is intelligent and will try casting these spells on the least threatened possible tiles first.\nThe walker cannot cast spells with 0 range, spells that can summon multiple minions, or spells that cannot target empty tiles.", "technical")
        self.upgrades['quaking'] = (1, 5, "Terraforming Kit", "The siege walker will emit seismic waves affecting a 4-tile radius.\nAffected walls and chasms have a 50% chance to become a floor tile.", "technical")
        self.upgrades['artillery'] = (1, 6, "Siege Artillery", "The siege walker gains a long-range mortar that deals [fire] damage equal to half its melee damage in a 2 tile radius and destroys walls in affected tiles.\nThe walker can use this attack with a 3 turn cooldown.", "technical")

    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['true_hp'] = d['minion_health']*20
        return d

    def can_cast(self, x, y):
        if not Level.Spell.can_cast(self, x, y):
            return False
        return self.caster.level.can_stand(x, y, self.make_siege()) and not any(u.source == self for u in self.caster.level.units)

    def get_description(self):
        return (
            "Summon a massive siege walker in the shape of a spider.\n"
            "The walker has [{true_hp}_HP:minion_health] and is a [metallic] unit, occupying a radius of 1 tile around its center due to its immense size.\n"
            "The walker has a melee attack dealing [{minion_damage}_physical_damage:physical].\n"
            "This spell benefits 20 times as much as normal from minion health bonuses, including its own upgrades.\n"
            "Only one siege walker may exist at a time."
            ).format(**self.fmt_dict())
            
    def get_extra_examine_tooltips(self):
        return [self.make_siege(),
                self.spell_upgrades[0],
                self.spell_upgrades[1],
                self.spell_upgrades[2]
                ]
    
    def make_siege(self):
        walker = Level.Unit()
        walker.name = "Siege Walker"
        walker.tags = [Level.Tags.Metallic, Level.Tags.Construct]
        walker.radius = 1
        walker.max_hp = self.get_stat('minion_health')*20
        walker.asset_name = os.path.join("..","..","mods","FirstMod","3x3_siege_walker")
        walker.spells.append(CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage')))
        if self.get_stat('ally'):
            eligibles = [s for s in self.caster.spells if s.level <= 4 and s.can_target_empty and not s.get_stat('num_summons') and s.range]
            eligibles.sort(key=lambda x: x.level)
            if eligibles:
                summon = type(eligibles[0])()
                summon.caster = walker
                summon.owner = walker
                summon.statholder = self.caster
                summon.cool_down = 10
                walker.spells.insert(0, summon)
                def intelligent_call():
                    castable_points = [t for t in self.caster.level.iter_tiles() if summon.can_cast(t.x, t.y)]
                    if not castable_points:
                        return None
                    enemies = [u for u in self.caster.level.units if Level.are_hostile(u, summon.caster)]
                    threat_dict = {}
                    for c in castable_points:
                        for e in enemies:
                            ct = 0
                            for s in e.spells:
                                if s.can_threaten(c.x, c.y):
                                    ct += 1
                            threat_dict[Level.Point(c.x, c.y)] = ct
                    if threat_dict:
                        return min(threat_dict, key=threat_dict.get)
                    else:
                        return random.choice(castable_points)
                summon.get_ai_target = intelligent_call
        elif self.get_stat('quaking'):
            walker.buffs.append(SiegeQuake())
        elif self.get_stat('artillery'):
            walker.spells.insert(0, CommonContent.SimpleRangedAttack(name="Siege Mortar", damage=self.get_stat('minion_damage')//2, damage_type=Level.Tags.Fire, range=15+self.get_stat('minion_range'), radius=2, melt=True, cool_down=3))
        walker.is_unique = True
        return walker
    
    def cast_instant(self, x, y):
        self.summon(self.make_siege(), Level.Point(x, y))

class BigSpell(Level.Spell):
    def on_init(self):
        self.name = "Spatial Expansion"
        self.max_charges = 3
        self.range = 9
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane]
        self.level = 6

        self.can_target_empty = False
        self.requires_los = False

        self.upgrades['radial'] = (1, 4, "Chain Expansion", "Targeted units gain 2 [radius] to all abilities.")
        self.upgrades['boost'] = (1, 3, "Greater Expansion", "Targeted units gain triple HP as opposed to double.")

    def can_cast(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        if u and not Level.are_hostile(u, self.caster) and Level.Spell.can_cast(self, x, y) and not u.radius:
            contiguous = self.owner.level.get_points_in_ball(x, y, 1, diag=True)
            for t in contiguous:
                if t.x == x and t.y == y:
                    continue
                elif not self.caster.level.can_stand(t.x, t.y, u):
                    return False
            return True

    def get_description(self):
        return "Target minion's current and maximum HP doubles, and it also becomes a multi-tile unit, occupying a radius of 1 around itself.\nCannot be used on units that are already multi-tile.".format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        u.max_hp *= 2 + self.get_stat('boost')
        u.cur_hp *= 2 + self.get_stat('boost')
        u.radius = 1
        if self.get_stat('radial'):
            b = CommonContent.GlobalAttrBonus('radius', 2)
            b.buff_type = Level.BUFF_TYPE_BLESS
            b.name = "Chain Expansion"
            u.apply_buff(b)

class MinionLichForm(Level.Spell):
    def on_init(self):
        self.name = "Ritual of Undeath"
        self.max_charges = 1
        self.range = 5
        self.tags = [Level.Tags.Enchantment, Level.Tags.Dark]
        self.level = 7

        self.can_target_empty = False

        self.upgrades['max_charges'] = (1, 3)

    def can_cast(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        return u and not Level.are_hostile(u, self.caster) and Level.Spell.can_cast(self, x, y)

    def get_description(self):
        return "Target minion becomes a lich, gaining [undead], 100 [dark] and [poison] resist, and losing 100 [holy] resist.\nIt also gains the ability to summon a soul jar that protects it from death.".format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        if not u:
            return
        jar = CommonContent.LichSealSoulSpell()
        jar.owner = u
        jar.caster = u
        jar.statholder = u
        u.spells.insert(0, jar)
        u.resists[Level.Tags.Dark] += 100
        u.resists[Level.Tags.Poison] += 100
        u.resists[Level.Tags.Holy] -= 100
        u.name = "%s Lich" % u.name
        u.outline_color = Level.Color(156, 39, 176)
        if Level.Tags.Undead not in u.tags:
            u.tags.append(Level.Tags.Undead)

class HoopsPaint(Level.Spell):
    def on_init(self):
        self.name = "Paint Splash"
        self.range = 1
        self.radius = 1
        self.damage = 1
        self.range = 2
    def get_description(self):
        return "Splashes paint, dealing damage of a random type.".format(**self.fmt_dict())
    def cast(self, x, y):
        for spread in CommonContent.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius')):
            for point in spread:
                u = self.caster.level.get_unit_at(point.x, point.y)
                if u and (u == self.caster or not Level.are_hostile(u, self.caster)):
                    continue
                dtype = random.choice([Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Physical, Level.Tags.Arcane, Level.Tags.Holy, Level.Tags.Dark, Level.Tags.Poison])
                self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), dtype, self)
            yield

class HoopsStroke(Level.Spell):
    def on_init(self):
        self.name = "Stroke of Genius"
        self.range = 50
        self.damage = 1
        self.cool_down = 8
        self.get_impacted_tiles = Spells.IceWind.get_impacted_tiles
        self.requires_los = False
    def get_description(self):
        return "Strokes with a massive paintbrush, dealing damage in a perpendicular line.\nDoes not require line of sight to use.".format(**self.fmt_dict())
    def cast(self, x, y):
        for point in self.get_impacted_tiles(self, x, y):
            u = self.caster.level.get_unit_at(point.x, point.y)
            if u and (u == self.caster or not Level.are_hostile(u, self.caster)):
                continue
            dtype = random.choice([Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Physical, Level.Tags.Arcane, Level.Tags.Holy, Level.Tags.Dark, Level.Tags.Poison])
            self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), dtype, self)
        yield
    
class HoopsCounter(Level.Buff):
    def on_init(self):
        self.name = "Paint Barrier"
        self.color = Level.Tags.Chaos.color
        self.global_triggers[Level.EventOnPreDamaged] = self.palette_counter

    def get_tooltip(self):
        return "Whenever this unit blocks damage from an enemy spell due to shield, casts that spell back at the target if possible."  
    
    def palette_counter(self, evt):
        if Level.Spell not in type(evt.source).__bases__:
            return
        if not evt.source.owner:
            return
        if evt.damage > 0 and self.owner.resists[evt.damage_type] < 100 and self.owner.shields > 1 and Level.are_hostile(evt.source.owner, self.owner):
            mimed = copy.copy(evt.source)
            mimed.statholder = self.owner
            mimed.caster = self.owner
            mimed.owner = self.owner
            if mimed.can_cast(evt.source.owner.x, evt.source.owner.y):
                self.owner.level.act_cast(self.owner, mimed, evt.source.owner.x, evt.source.owner.y)
    
class Hoops(Level.Spell):

    def on_init(self):

        self.name = "Imp Artist"
        self.max_charges = 1
        self.range = 6
        self.tags = [Level.Tags.Conjuration, Level.Tags.Chaos]
        self.level = 7
        self.minion_health = 55
        self.shields = 4
        self.minion_damage = 8
        self.radius = 2
        self.minion_range = 10
        self.must_target_empty = True

        self.upgrades['genius'] = (1, 4, "Stroke of Genius", "The imp can make massive strokes with a paintbrush, dealing damage of random type to each tile in a line perpendicular to itself.\nThis ability has an 8 turn cooldown.", "style")
        self.upgrades['palette'] = (1, 5, "Palette Shield", "Whenever the imp blocks enemy spell damage due to shield, the imp will mimic that spell back onto the enemy if possible.\nThe imp's mimed version of the spell benefits from all applicable bonuses the imp would get to that spell.", "style")
        self.upgrades['sculpt'] = (1, 4, "Sprite Drawing", "The imp can draw animated constructs, allowing it to summon 3 glass, clay, or junk golems lasting 14 turns.\nThis ability has a 10 turn cooldown.", "style")

    def get_impacted_tiles(self, x, y):
        return [Level.Point(x, y)]

    def get_description(self):
        return (
            "Summon a familiar imp with an eye for art.\n"
            "This imp has [{minion_health}_HP:minion_health], [{shields}_SH:shield], 100 [poison] resist, and can fly.\n"
            "The imp can attack enemies in [{minion_range}_tiles:range] with its painting tools, dealing [{minion_damage}_damage:damage] of a random type in a [{radius}-tile_burst:radius]. The imp and its allies are unaffected by this attack.\n"
            "The imp is also immune to incapacitating debuffs like [stun]."
            ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.make_siege(),
                self.spell_upgrades[0],
                self.spell_upgrades[1],
                self.spell_upgrades[2]
                ]
    
    def make_siege(self):
        walker = Level.Unit()
        walker.name = "Imp Artist"
        walker.tags = [Level.Tags.Demon]
        walker.max_hp = self.get_stat('minion_health')
        walker.shields = self.get_stat('shields')
        walker.asset_name = os.path.join("..","..","mods","FirstMod","imp_artist")
        walker.resists[Level.Tags.Poison] = 100
        walker.resists[Level.Tags.Holy] = 0
        walker.resists[Level.Tags.Dark] = 0
        walker.buffs.append(Level.StunImmune())
        if self.get_stat('sculpt'):
            def randgol():
                u = random.choice([Monsters.GlassGolem, Monsters.Golem, Variants.GolemClay])()
                u.turns_to_death = 14
                return u
            golem = CommonContent.SimpleSummon(randgol, num_summons=3, cool_down=10)
            golem.description = "Summons 3 clay golems, glass golems, or golems randomly for 14 turns"
            golem.name = "Sprite Draw"
            walker.spells.append(golem)
        if self.get_stat('genius'):
            brush = HoopsStroke()
            brush.damage = self.get_stat('minion_damage') + 4
            walker.spells.append(brush)
        paint = HoopsPaint()
        paint.damage = self.get_stat('minion_damage')
        paint.range = self.get_stat('minion_range')
        paint.radius = self.get_stat('radius')
        walker.spells.append(paint)
        if self.get_stat('palette'):
            walker.buffs.append(HoopsCounter())
        walker.flying = True
        return walker
    
    def cast_instant(self, x, y):
        self.summon(self.make_siege(), Level.Point(x, y))

class FlyStun(Level.Buff):
    def on_init(self):
        self.name = "Fly Stun"
        self.color = Level.Tags.Physical.color

    def on_advance(self):
        for q in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, 1.5):
            if q.x == self.owner.x and q.y == self.owner.y:
                continue
            u = self.owner.level.get_unit_at(q.x, q.y)
            if u and Level.are_hostile(u, self.owner):
                u.apply_buff(Level.Stun(), 1)

    def get_tooltip(self):
        return "Stuns adjacent enemies for 1 turn each turn."

class FlyTrap(Level.Spell):

    def on_init(self):

        self.name = "Fly Trap"
        self.max_charges = 5
        self.range = 6
        self.tags = [Level.Tags.Conjuration, Level.Tags.Nature, Level.Tags.Dark]
        self.level = 2
        ex = RareMonsters.FlyTrap()
        self.minion_health = ex.max_hp
        self.minion_range = ex.spells[1].range
        self.num_summons = ex.spells[0].num_summons
        self.must_target_walkable = True
        self.must_target_empty = True

        self.upgrades['num_summons'] = (2, 3)
        self.upgrades['leaf'] = (1, 4, "Sticky Leaves", "Fly traps stun enemies adjacent to them for 1 turn each turn.")

    def get_description(self):
        return (
            "Summon a fly trap on target tile.\n"
            ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.make_siege(),
                self.spell_upgrades[0],
                self.spell_upgrades[1],
                ]
    
    def make_siege(self):
        walker = RareMonsters.FlyTrap()
        CommonContent.apply_minion_bonuses(self, walker)
        walker.spells[0].num_summons = self.get_stat('num_summons')
        walker.spells[0].description = "Summons %d Fly Swarms" % self.get_stat('num_summons')
        if self.get_stat('leaf'):
            walker.buffs.append(FlyStun())
        return walker
    
    def cast_instant(self, x, y):
        self.summon(self.make_siege(), Level.Point(x, y))

class ProvokeBuff(Level.Buff):
    def __init__(self, target, spell):
        self.target = target
        self.spell = spell
        Level.Buff.__init__(self)
        self.name = "Provoked"
        self.color = Level.Tags.Blood.color
        self.targeters = {}
        self.can_harm_old = None

    def on_applied(self, owner):
        self.can_harm_old = self.owner.can_harm
        def provoke_harm(other):
            if self.can_harm_old(self.target):
                return other == self.target
        owner.can_harm = provoke_harm

    def on_pre_advance(self):
        if not self.target.is_alive():
            self.owner.remove_buff(self)
        for s in self.owner.spells:
            if s not in list(self.targeters.keys()):
                self.modify_spell(s)
    
    def on_unapplied(self):
        self.owner.can_harm = self.can_harm_old

    def modify_spell(self, spell):
        old = spell.get_ai_target
        if spell.get_stat('range') > 0:
            def provoke_target(*args, **kwargs):
                if spell.can_cast(self.target.x, self.target.y):
                    return self.target
                return None
            self.targeters[spell] = old
            spell.get_ai_target = provoke_target
        elif self.spell.get_stat('manup'):
            def unusable(*args, **kwargs):
                return None
            self.targeters[spell] = old
            spell.get_ai_target = unusable

    def unmodify_spell(self, spell):
        if spell in self.targeters:
            spell.get_ai_target = self.targeters[spell]

class Taunt(Level.Spell):

    def on_init(self):

        self.name = "Taunt"
        self.max_charges = 5
        self.range = 7
        self.tags = [Level.Tags.Enchantment, Level.Tags.Dark]
        self.level = 4
        self.duration = 15
        self.radius = 4

        self.upgrades['requires_los'] = (1, 4, "Blindcasting", "Taunt can be cast without line of sight.")
        self.upgrades['nerf'] = (1, 4, "Tinge of Fear", "[Provoked:blood] units suffer a -20% penalty to all spell damage.")
        self.upgrades['manup'] = (1, 7, "True Taunt", "Zero-range abilities cannot be used while [provoked:blood].")

    def can_cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        return u and not u.turns_to_death and not Level.are_hostile(u, self.caster) and Level.Spell.can_cast(self, x, y)

    def get_description(self):
        return (
            "Enemies in [{radius}_tiles:radius] of target ally are [provoked:blood] for [{duration}_turns:duration].\n"
            "A [provoked:blood] unit will always move towards the target ally, and may only use spells with range greater than 0 on that ally.\n"
            "May only be cast on permanent minions."
            ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        taunter = self.caster.level.get_unit_at(x, y)
        if not taunter:
            return
        provokees = [u for u in self.caster.level.get_units_in_ball(Level.Point(x, y), self.get_stat('radius')) if Level.are_hostile(u, taunter)]
        for p in provokees:
            provoke = ProvokeBuff(taunter, self)
            if self.get_stat('nerf'):
                provoke.global_bonuses_pct['damage'] = -20.0
            p.apply_buff(provoke, self.get_stat('duration'))

class CrabHasteBuff(Level.Buff):
    def __init__(self, actions, spell):
        self.actions = actions
        self.spell = spell
        Level.Buff.__init__(self)
        self.name = "Haste"
        self.color = Level.Tags.Ice.color
    
    def get_tooltip(self):
        return "Takes an extra %d actions per turn" % self.actions

    def on_advance(self):
        for _ in range(self.actions):
            if not self.owner.is_alive():
                break
            self.owner.level.leap_effect(self.owner.x, self.owner.y, Level.Tags.Nature.color, self.owner)
            if self.spell.get_stat('outrage'):
                self.owner.cool_downs = { spell : 1 for (spell, cooldown) in self.owner.cool_downs.items() if cooldown > 1}
            self.owner.advance()

class Buffproof(Level.Buff):
    def on_init(self):
        self.name = "Reverse Immunity"
        self.color = Level.Tags.Fire.color
        self.owner_triggers[Level.EventOnBuffApply] = self.on_apply
        self.buff_type = Level.BUFF_TYPE_PASSIVE
    
    def get_tooltip(self):
        return "Immune to damage-enhancing positive effects"

    def on_apply(self, evt):
        if evt.buff.buff_type == Level.BUFF_TYPE_BLESS and (evt.buff.global_bonuses['damage'] > 0 or evt.buff.global_bonuses_pct['damage'] > 0):
            self.owner.remove_buff(evt.buff)

class Krabby(Level.Spell):

    def on_init(self):

        self.name = "Abominable Crab"
        self.max_charges = 5
        self.range = 2
        self.tags = [Level.Tags.Conjuration, Level.Tags.Nature, Level.Tags.Ice]
        self.level = 5
        self.minion_health = 40
        self.minion_damage = 12
        self.turn_threshold = 2
        self.stats.append('turn_threshold')
        self.must_target_walkable = True
        self.must_target_empty = True

        self.upgrades['bloodlust'] = (1, 4, "Bloodseeker", "The crab gets 1 turn of bloodrage when summoned, increasing the damage of all of its abilities by 4.\nThis is considered a passive effect.")
        self.upgrades['outrage'] = (1, 5, "Unyielding Abomination", "The crab's ability cooldowns reset before each of its extra actions.")

    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['num_acts'] = (self.get_stat('minion_damage') - 4) // self.get_stat('turn_threshold')
        return d

    def get_description(self):
        return (
            "Summon the abominable crab on target tile.\n"
            "The abominable crab is a [living] [nature] [ice] unit with [{minion_health}_HP:minion_health], 100 [ice] resist, and 50 [physical] resist, and a melee attack dealing 3 [physical] damage.\n"
            "The crab's attacks deal fixed damage, but for every [{turn_threshold}:ice] [minion_damage:minion_damage] this spell has beyond 4, the crab can act 1 extra time each turn.\n"
            "The crab is additionally immune to positive effects that increase the damage of its abilities.\n"
            "This spell has [{minion_damage}_minion_damage:minion_damage], so the crab currently acts [{num_acts}:heal] extra times."
            ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.make_siege(),
                self.spell_upgrades[0],
                self.spell_upgrades[1]
                ]
    
    def make_siege(self):
        walker = Level.Unit()
        walker.name = "Abominable Crab"
        walker.asset_name = os.path.join("..","..","mods","FirstMod","crab_abominable")
        walker.tags = [Level.Tags.Living, Level.Tags.Ice, Level.Tags.Nature]
        walker.resists[Level.Tags.Ice] = 100
        walker.resists[Level.Tags.Physical] = 50
        walker.max_hp = self.get_stat('minion_health')
        walker.spells.append(CommonContent.SimpleMeleeAttack(3))
        num_acts = (self.get_stat('minion_damage') - 4) // self.get_stat('turn_threshold')
        if num_acts > 0:
            walker.buffs.append(CrabHasteBuff(num_acts, self))
        walker.buffs.append(Buffproof())
        return walker

    def cast_instant(self, x, y):
        u = self.make_siege()
        self.summon(u, Level.Point(x, y))
        if self.get_stat('bloodlust'):
            bloodrage = CommonContent.BloodrageBuff(4)
            bloodrage.buff_type = Level.BUFF_TYPE_PASSIVE
            u.apply_buff(bloodrage, 2)
            

class Affordance(Level.Buff):
    def __init__(self, tag):
        self.tag = tag
        Level.Buff.__init__(self)
        self.color = tag.color
        self.name = "%s Affordance" % tag.name
        self.stack_type = Level.STACK_DURATION

class TheHarvestBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnDeath] = self.on_death
        self.owner_triggers[Level.EventOnSpellCast] = self.on_cast
        self.color = Level.Tags.Enchantment.color
        self.name = "Elemental Harvest"
        self.stack_type = Level.STACK_DURATION 
        self.valid_tags = [Level.Tags.Ice, Level.Tags.Fire, Level.Tags.Lightning]
    
    def on_death(self, evt):
        valids = [t for t in evt.unit.tags if t in self.valid_tags]
        if not valids:
            return
        for t in valids:
            buff = Affordance(t)
            self.owner.apply_buff(buff, evt.unit.max_hp)

    def on_cast(self, evt):
        valids = [t for t in evt.spell.tags if t in self.valid_tags]
        if not valids or type(evt.spell) == TheHarvest:
            return
        threshold = self.spell.get_stat('duration_per_level')*evt.spell.level + (max(0, evt.spell.level-4)*self.spell.get_stat('duration_per_level'))*(1-self.get_stat('adept'))
        affordances = [a for a in self.owner.buffs if type(a) == Affordance and a.tag in valids and a.turns_left >= threshold]
        if not affordances:
            return
        affordance = max(affordances, key = lambda x: x.turns_left)
        affordance.turns_left -= threshold
        evt.spell.cur_charges = min(evt.spell.cur_charges+1, evt.spell.max_charges)
        

class TheHarvest(Level.Spell):
    def on_init(self):
        self.name = "Elemental Affordance"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning]
        self.level = 5
        self.duration = 25
        self.duration_per_level = 25
        self.stats.append('duration_per_level')

        self.upgrades['duration_per_level'] = (-5, 3, "Flexibility", "Each spell level costs 5 less Affordance duration to refund.")
        self.upgrades['adept'] = (1, 5, "Harvest Adept", "Spells that are above level 4 no longer cost extra Affordance duration.")

    def get_description(self):
        return (
            "Gain Elemental Harvest for [{duration}_turns:duration].\n"
            "Whenever a [fire], [ice], or [lightning] unit dies while you have Elemental Harvest, gain Affordance X for its respective tag, where X is the unit's maximum HP.\n"
            "Units with more than one of those tags will grant the buff for all of them that they had on death. Affordance buffs stack in duration.\n"
            "Whenever you cast a [fire], [ice], or [lightning] spell while Elemental Harvest is active, except this one, consume [{duration_per_level}:arcane] duration per spell level and refund the spent charge.\n"
            "Spells that are above level 4 cost an extra [{duration_per_level}:arcane] duration per spell level above 4.\n"
            "The Affordance with the highest duration will always be consumed first."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.owner.apply_buff(TheHarvestBuff(self), self.get_stat('duration'))

class JarAllyPlus(Level.Spell):

    def __init__(self, source_spell):
        self.source_spell = source_spell
        Level.Spell.__init__(self)

    def on_init(self):
        self.name = "Pickle Soul"
        self.range = 10

    def get_description(self):
        return "A non-construct ally loses %d max HP, but cannot die until the Jar is destroyed. Cannot target the Wizard." % self.source_spell.get_stat('hp_penalty')

    def get_ai_target(self):
        candidates = [u for u in self.caster.level.get_units_in_los(self.caster) if not Level.are_hostile(u, self.caster) and not u.has_buff(CommonContent.Soulbound) and Level.Tags.Construct not in u.tags]
        candidates = [u for u in candidates if self.can_cast(u.x, u.y) and not u.is_player_controlled]
        
        if not candidates:
            return None
        return random.choice(candidates)

    def cast(self, x, y):

        for p in self.caster.level.get_points_in_line(self.caster, Level.Point(x, y), find_clear=True)[1:-1]:
            self.caster.level.deal_damage(p.x, p.y, 0, Level.Tags.Dark, self)
            yield

        unit = self.caster.level.get_unit_at(x, y)
        if not unit:
            return

        unit.max_hp -= self.source_spell.get_stat('hp_penalty')
        unit.max_hp = max(1, unit.max_hp)
        unit.cur_hp = min(unit.cur_hp, unit.max_hp)

        buff = CommonContent.Soulbound(self.caster)
        unit.apply_buff(buff)

class BeegJar(Level.Spell):
    def on_init(self):
        self.name = "Giant Soul Jar"
        self.max_charges = 1
        self.range = 5
        self.tags = [Level.Tags.Conjuration, Level.Tags.Dark, Level.Tags.Arcane]
        self.level = 7
        self.minion_health = 70
        self.must_target_empty = True
        self.must_target_walkable = True
        self.hp_penalty = 10
        self.stats.append('hp_penalty')

        self.upgrades['hp_penalty'] = (-5, 3, "Efficient Pickling", "Jarred allies lose 5 less max HP.")
        self.upgrades['holier'] = (1, 6, "Revelation of Undeath", "The jar spawns with Touched by Holy, removing its weakness to [holy] damage and granting it a ranged attack dealing [holy] damage.")
        self.upgrades['steel'] = (1, 5, "Metal Jar", "The jar gains the [metallic] modifier.")
    
    def can_cast(self, x, y):
        return Level.Spell.can_cast(self, x, y) and not any(u.source == self for u in self.caster.level.units)

    def get_description(self):
        return (
            "Summon a giant soul jar on target tile.\n"
            "The jar is a [dark] [arcane] [construct] with [{minion_health}_HP:minion_health].\n"
            "The jar is immune to [dark] and [poison], takes half damage from [arcane] and [fire], takes 50% extra [physical] damage, and double damage from [holy].\n"
            "The jar has no attacks of its own, but can pickle the souls of its allies, decreasing their max HP by [{hp_penalty}:dark] and making them unable to be killed while the jar is alive. This cannot decrease their max HP below 1.\n"
            "This ability cannot target [construct] units or the Wizard.\n"
            "You may only summon one giant soul jar at a time."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.jar(),
                self.spell_upgrades[0],
                self.spell_upgrades[1],
                ]

    def jar(self):
        mon = RareMonsters.GiantSoulJar()
        mon.spells[0] = JarAllyPlus(self)
        CommonContent.apply_minion_bonuses(self, mon)
        mon.max_hp = self.get_stat('minion_health')
        mon.is_unique = True
        if self.get_stat('steel'):
            BossSpawns.apply_modifier(BossSpawns.Metallic, mon)
        return mon

    def cast_instant(self, x, y):
        u = self.jar()
        self.summon(u, Level.Point(x, y))
        if self.get_stat('holier'):
            b = CommonContent.TouchedBySorcery(Level.Tags.Holy)
            b.asset = Spells.PurityBuff().asset
            u.apply_buff(b)

class TransfusionBuff(Level.Buff):
    def __init__(self, spell, donor):
        self.spell = spell
        self.donor = donor
        Level.Buff.__init__(self)
        self.color = Level.Tags.Blood.color
        self.mag = math.ceil(self.spell.get_stat('hp_cost')*(1+(self.spell.get_stat('efficacy')/2)))
        self.to_regen = self.spell.get_stat('hp_cost')//(2-self.spell.get_stat('recover'))
        self.name = "Transfusion %d" % self.mag
        self.applied_living = False

    def on_applied(self, owner):
        owner.max_hp += self.mag
        if self.spell.get_stat('living') and Level.Tags.Living not in owner.tags:
            owner.tags.append(Level.Tags.Living)
            self.applied_living = True
        if self.spell.get_stat('recover'):
            self.owner.deal_damage(-self.mag, Level.Tags.Heal, self.spell)

    def on_unapplied(self):
        self.owner.max_hp = max(1, self.owner.max_hp-self.mag)
        self.owner.cur_hp = min(self.owner.cur_hp, self.owner.max_hp)
        self.donor.deal_damage(-self.to_regen, Level.Tags.Heal, self.spell)
        if self.applied_living:
            self.owner.tags.remove(Level.Tags.Living)


class BloodDrive(Level.Spell):
    def on_init(self):
        self.name = "Transfusion"
        self.max_charges = 5
        self.range = 8
        self.requires_los = False
        self.tags = [Level.Tags.Blood, Level.Tags.Enchantment]
        self.level = 3
        self.duration = 25
        self.hp_cost = 13

        self.upgrades['efficacy'] = (1, 3, "Efficacy", "Transfusion gives targets an extra 50% of the HP cost as maximum HP, rounded up.")
        self.upgrades['living'] = (1, 2, "Soul Link", "Targets that are not already [living] gain [living] for the duration of the spell.")
        self.upgrades['recover'] = (1, 5, "Full Recovery", "Targets heal for an amount equal to the max HP they gained when hit by the spell.\nAt the end of the spell's duration, you heal the full amount transferred instead of half.")

    def can_cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        return u and not Level.are_hostile(u, self.caster) and Level.Spell.can_cast(self, x, y) and not u.has_buff(TransfusionBuff)

    def get_description(self):
        return (
            "Donate some of your life force to target ally, giving it extra maximum HP equal to this spell's HP cost.\n"
            "The effect lasts [{duration}_turns:duration], after which you heal for half the amount you paid to cast this spell, rounded down.\n"
            "This spell cannot target allies that are already affected."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if u:
            u.apply_buff(TransfusionBuff(self, self.caster), self.get_stat('duration'))

class InsectRush(Level.Spell):
    def on_init(self):
        self.name = "Mantodean Ambush"
        self.max_charges = 6
        self.range = 0
        self.tags = [Level.Tags.Conjuration, Level.Tags.Nature]
        self.level = 2
        self.radius = 6

        ex = Monsters.Mantis()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage
        self.minion_range = ex.spells[1].range

        self.upgrades['radius'] = (3, 5, "Expanding Territory")
        self.upgrades['ghost'] = (1, 4, "Phantom Ambush", "Summon ghostly mantises instead of normal ones.")
        self.upgrades['clay'] = (1, 4, "Earthen Ambush", "Summon clay mantises instead of normal ones.")
        self.upgrades['volt'] = (1, 3, "Teravolt Ambush", "Summon electric mantises instead of normal ones.")

        #upgrework ideas
        #big ass radius upgrade? hella mantises but no firepower (6 rad base so 2 is more than enough for a nice boost)
        #clay ambush, new + steels are kinda shit anyway, regen is better than ice resist given their hp & the difference between 50 and 75 res isnt super impactful
        #electr can stay the same perhaps, fae would be kinda mid since ghosts spike better and shield regen is meh given theyll be hit by multiple sources at once
        #ghosts can probably stay, their hp doesnt matter as much since theyre affected by WoU, and phy immune lets them carry early
        #burning could come along but it would have to be much more expensive than the others since they have aura access
        #liches would also be pretty good, theoretically infinite uptime but you would need to defend the jars, also WoU and spikes compatible
        #were would be strictly worse than clay, the wolf would have ultra shit hp and it gives zero resists aside from dark which liches and ghosts give immunity to
        #immortal would be too good, free 2 extra lives is op as hell, mass immortality can do that but thats 2 extra turns and 6 sp
        #chaos op, floating into boosted imps is busted with their numbers and the chaos attack is actually good (plus imps nature lord, lmao even)
        #ice could be decent but no better than electr, 1 shield is actually impactful given their hp and having a nonphysical pounce is a major plus
        #troll is just worse were (no wolf + regen is conditional) which is already worse than clay
        
    def get_description(self):
        return (
            "Summon a mantis near each enemy unit in a [{radius}-tile_radius:radius].\n"
            "Mantises have [{minion_health}_HP:minion_health] and melee attacks dealing [{minion_damage}_physical_damage:physical].\n"
            "Mantises also have leap attacks dealing the same damage with a [{minion_range}-tile_range:range]."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.mantis_base(),
                self.spell_upgrades[0],
                self.spell_upgrades[1],
                self.mantis_ghost(),
                self.spell_upgrades[2],
                self.mantis_clay(),
                self.spell_upgrades[3],
                self.mantis_electr()
                ]

    def mantis_base(self):
        m = Monsters.Mantis()
        return m
    
    def mantis_ghost(self):
        m = BossSpawns.apply_modifier(BossSpawns.Ghostly, Monsters.Mantis())
        return m

    def mantis_clay(self):
        m = BossSpawns.apply_modifier(BossSpawns.Claytouched, Monsters.Mantis())
        return m

    def mantis_electr(self):
        m = BossSpawns.apply_modifier(BossSpawns.Stormtouched, Monsters.Mantis())
        return m

    def cast_instant(self, x, y):
        victims = [u for u in self.caster.level.get_units_in_ball(Level.Point(x, y), self.get_stat('radius')) if Level.are_hostile(u, self.caster)]
        if not victims:
            return
        for v in victims:
            if self.get_stat('ghost'):
                m = self.mantis_ghost()
            elif self.get_stat('clay'):
                m = self.mantis_clay()
            elif self.get_stat('volt'):
                m = self.mantis_electr()
            else:
                m = self.mantis_base()
            CommonContent.apply_minion_bonuses(self, m)
            self.summon(m, v, radius=7)

class LionCall(Level.Spell):
    def on_init(self):
        self.name = "Roar of the Pride"
        self.max_charges = 4
        self.range = 0
        self.tags = [Level.Tags.Conjuration, Level.Tags.Nature, Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Arcane]
        self.level = 4

        ex = Monsters.RedLion()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage
        self.minion_range = ex.spells[0].range

        self.upgrades['giant'] = (1, 5, "Great Pride", "Summon giant lions instead of regular ones.\nGiant lions have double HP and deal increased damage.")

    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['ranged_damage'] = d['minion_damage']-1
        return d

    def get_description(self):
        return (
            "Summon a fire lion, ice lion, and star lion near yourself."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.starlion(),
                self.redlion(),
                self.icelion(),
                self.spell_upgrades[0],
                self.starlion(True),
                self.redlion(True),
                self.icelion(True)
                ]
    
    def starlion(self, gig=False):
        l = Monsters.StarLion() if not gig else Variants.StarfireLionGiant()
        CommonContent.apply_minion_bonuses(self, l)
        if gig:
            l.max_hp = self.get_stat('minion_health')*2
        return l

    def redlion(self, gig=False):
        l = Monsters.RedLion() if not gig else Variants.ChaosLionGiant()
        CommonContent.apply_minion_bonuses(self, l)
        if gig:
            l.max_hp = self.get_stat('minion_health')*2
        return l

    def icelion(self, gig=False):
        l = Monsters.IceLion() if not gig else Variants.DeathchillLionGiant()
        CommonContent.apply_minion_bonuses(self, l)
        if gig:
            l.max_hp = self.get_stat('minion_health')*2
        return l

    def cast_instant(self, x, y):
        for lion in [self.starlion(bool(self.get_stat('giant'))), self.redlion(bool(self.get_stat('giant'))), self.icelion(bool(self.get_stat('giant')))]:
            self.summon(lion, self.caster)

class MedusaBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.owner_triggers[Level.EventOnDamaged] = self.on_damage
        self.global_triggers[Level.EventOnSpellCast] = self.on_spell_cast
        self.color = Level.Tags.Nature.color
        self.name = "Medusa Form"
        self.stack_type = Level.STACK_TYPE_TRANSFORM
        self.transform_asset_name = "medusa"
        self.counter = 0
        self.step = 4

    def on_damage(self, evt):
        self.counter += evt.damage
        while self.counter >= self.step:
            m = self.spell.snake_base()
            if self.spell.get_stat('death'):
                m = self.spell.snake_dark()
            if self.spell.get_stat('lit'):
                m = self.spell.snake_gold()
            if self.spell.get_stat('lava'):
                m = self.spell.snake_fire()
            self.summon(m, self.owner)
            self.counter -= self.step

    def on_spell_cast(self, evt):
        if evt.caster == self.owner or evt.x != self.owner.x or evt.y != self.owner.y:
            return
        evt.caster.apply_buff(CommonContent.PetrifyBuff(), 2)
        
class MedusaForm(Level.Spell):
    def on_init(self):
        self.name = "Medusa Form"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane, Level.Tags.Nature, Level.Tags.Conjuration]
        self.level = 4
        self.duration = 21

        ex = Monsters.Snake()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        #for purposes of marksman cap and whatnot
        ex2 = Monsters.GoldenSnake()
        self.minion_range = ex2.spells[0].range

        self.snake_base = lambda: self.sourceify(Monsters.Snake())
        self.snake_dark = lambda: self.sourceify(Monsters.DeathSnake())
        self.snake_gold = lambda: self.sourceify(Monsters.GoldenSnake())
        self.snake_fire = lambda: self.sourceify(Monsters.FireSnake())

        self.upgrades['death'] = (1, 4, "Dark Cobras", "Summon death snakes instead of normal snakes.", "element")
        self.upgrades['lava'] = (1, 5, "Burning Boas", "Summon fire snakes instead of normal snakes.", "element")
        self.upgrades['lit'] = (1, 3, "Electric Rattlers", "Summon lightning snakes instead of normal snakes.", "element")

    def get_description(self):
        return (
            "Transform into a medusa for [{duration}_turns:duration].\n"
            "Whenever an enemy targets you with an attack, petrify it for [2_turns:duration].\n"
            "For every 4 damage you take while in Medusa Form, summon a snake near you.\n"
            "Snakes have [{minion_health}_HP:minion_health] and melee attacks that deal [{minion_damage}_physical_damage:physical] and inflict [poison] for [5_turns:duration]."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.snake_base(),
                self.spell_upgrades[0],
                self.snake_dark(),
                self.spell_upgrades[1],
                self.snake_fire(),
                self.spell_upgrades[2],
                self.snake_gold()
                ]

    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        return m

    def cast_instant(self, x, y):
        self.owner.apply_buff(MedusaBuff(self), self.get_stat('duration'))

class GenericSpellSeal(Level.Buff):
    def __init__(self, seal_spell):
        self.seal_spell = seal_spell
        Level.Buff.__init__(self)
        self.name = "%s Seal" % self.seal_spell.name
        self.color = Level.Tags.Dark.color
        self.old = seal_spell.can_cast
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.prereq = self.seal_spell

    def modify_spell(self, spell):
        if type(spell) == type(self.seal_spell):
            def uncastable(*args, **kwargs):
                return False
            spell.can_cast = uncastable

    def unmodify_spell(self, spell):
        if type(spell) == type(self.seal_spell):
            spell.can_cast = self.old

    def on_unapplied(self):
        if self.turns_left > 0:
            for s in self.owner.spells:
                self.unmodify_spell(s)
            self.owner.apply_buff(GenericSpellSeal(self.seal_spell), self.turns_left)

    def get_tooltip(self):
        return "%s cannot be cast." % self.seal_spell.name

class DeathSealBuff(Level.Buff):
    def __init__(self, summoner, spell):
        self.summoner = summoner
        self.spell = spell
        self.threshold = 10
        Level.Buff.__init__(self)
        self.color = Level.Tags.Dark.color

    def on_init(self):
        self.name = "Shaman's Seal"
        self.owner_triggers[Level.EventOnDeath] = self.on_death

    def on_death(self, evt):
        valids = [s for s in self.summoner.spells if not any(type(getattr(b, "seal_spell", '')) == type(s) for b in self.owner.buffs)]
        if not valids:
            return
        to_seal = random.choice(valids)
        self.summoner.apply_buff(GenericSpellSeal(to_seal), self.threshold)

    def get_tooltip(self):
        return "On death, seals one of the caster's spells for %d turns, rendering it unusable." % self.threshold

class ShamanCall(Level.Spell):
    def on_init(self):
        self.name = "Shamans' Divination"
        self.max_charges = 1
        self.range = 0
        self.tags = [Level.Tags.Conjuration, Level.Tags.Nature]
        self.level = 7

        self.minion_health = 88
        self.minion_range = 0
        self.minion_damage = 0

        self.upgrades['trollism'] = (1, 5, "Troll Divination", "Also randomly summon an earth troll priest, earth troll coppermancer, or storm troll mystic.")
        self.upgrades['cold'] = (1, 4, "Blizzard Wizards", "Also randomly summon a yeti shaman or polar bear blizzard shaman.")

        self.minotaur_magma = lambda: self.sourceify(Variants.MinotaurMagmaShaman())
        self.ogre_blackblaze = lambda: self.sourceify(Variants.OgreBlackblaze())
        self.ogre_thunderbone = lambda: self.sourceify(Variants.OgreThunderbone())
        self.copper_troll = lambda: self.sourceify(Variants.EarthTrollCopperstaff())
        self.holy_troll = lambda: self.sourceify(Variants.EarthTrollPriest())
        self.arcane_troll = lambda: self.sourceify(Variants.StormTrollMystic())
        self.yeti = lambda: self.sourceify(Variants.YetiShaman())
        self.bear = lambda: self.sourceify(Variants.PolarBearShaman())

    def get_description(self):
        return (
            "Call forth a blackblaze shaman, minotaur magma shaman, and thunderbone shaman near yourself.\n"
            "Each shaman has [{minion_health}_HP:minion_health] and a wide array of resistances and abilities.\n"
            "Whenever a shaman dies, a random one of the Wizard's spells is sealed, rendering it unusable for 10 turns.\n"
            "This effect can seal this spell, but cannot stack on the same spell more than once. The sealing effect is considered a buff, and will reapply itself if dispelled early."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.minotaur_magma(),
                self.ogre_blackblaze(),
                self.ogre_thunderbone(),
                self.spell_upgrades[0],
                self.copper_troll(),
                self.holy_troll(),
                self.arcane_troll(),
                self.spell_upgrades[1],
                self.yeti(),    
                self.bear()
                ]
    
    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        m.max_hp = self.get_stat('minion_health')
        m.buffs.append(DeathSealBuff(self.caster, self))
        if self.get_stat('resist'):
            m.resists[Level.Tags.Poison] = 100
        return m

    def make_pride(self):
        pride = [self.minotaur_magma(), self.ogre_blackblaze(), self.ogre_thunderbone()]
        if self.get_stat('trollism'):
            pride.append(random.choice([self.copper_troll(), self.holy_troll(), self.arcane_troll()]))
        elif self.get_stat('cold'):
            pride.append(random.choice([self.yeti(), self.bear()]))
        return pride

    def cast_instant(self, x, y):
        for lion in self.make_pride():
            self.summon(lion, self.caster)

class TwilightSeer(Level.Spell):
    def on_init(self):
        self.name = "Celestial Alignment"
        self.max_charges = 1
        self.range = 7
        self.tags = [Level.Tags.Conjuration, Level.Tags.Dark, Level.Tags.Holy]
        self.level = 7

        self.must_target_empty = True
        self.must_target_walkable = True

        ex = RareMonsters.TwilightSeer()
        self.minion_health = ex.max_hp

        self.minion_damage = ex.spells[1].damage
        self.minion_range = ex.spells[1].range
        self.radius = ex.spells[1].radius
        self.reincarnation = ex.get_buff(CommonContent.ReincarnationBuff).lives
        self.stats.append('reincarnation')

        self.upgrades['reincarnation'] = (1, 5, "Reincarnation")
        self.upgrades['wide'] = (1, 3, "Encompassing Vision", "The seer's attacks benefit from bonuses to [radius], where applicable.")

    def can_cast(self, x, y):
        return Level.Spell.can_cast(x, y) and not any(u.source == self for u in self.caster.level.units)

    def get_impacted_tiles(self, x, y):
        return [Level.Point(x, y)]

    def get_description(self):
        return (
            "Summon the Twilight Seer on target tile.\n"
            "You may only summon one Twilight Seer at a time."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.make_pride()] + self.spell_upgrades

    def make_pride(self):
        mon = RareMonsters.TwilightSeer()
        CommonContent.apply_minion_bonuses(self, mon)
        mon.buffs.clear()
        mon.buffs.append(CommonContent.ReincarnationBuff(self.get_stat('reincarnation')))
        if self.get_stat('wide'):
            diff = self.get_stat('radius') - self.radius
            for s in mon.spells:
                if getattr(s, 'radius', 0) > 0:
                    s.radius += diff
        return mon

    def cast_instant(self, x, y):
        self.summon(self.make_pride(), Level.Point(x, y))

class LycanthropeBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnUnitAdded] = self.werewolfize_new
        self.color = Level.Tags.Blood.color
        self.name = "Night of Blood"

    def werewolfize_new(self, evt):
        if Level.are_hostile(evt.unit, self.owner) or evt.unit.is_lair:
            return
        if not evt.unit.source or Level.Spell not in type(evt.unit.source).__bases__ or Level.Tags.Orb in getattr(evt.unit.source, 'tags', []) or type(evt.unit.source) == type(self.spell):
            return
        if getattr(evt.unit, "is_from_lycanspell", False):
            return
        if evt.unit.has_buff(CommonContent.RespawnAs):
            if evt.unit.get_buff(CommonContent.RespawnAs).spawner.__name__ == "animal_spawn_fn":
                return
        BossSpawns.apply_modifier(BossSpawns.Lycanthrope, evt.unit)
        wolf_func = evt.unit.get_buff(CommonContent.RespawnAs).spawner
        def modified_wolf():
            wolf = wolf_func()
            mature_into = wolf.get_buff(CommonContent.MatureInto).spawner
            setattr(wolf, "is_from_lycanspell", True)
            if self.spell.get_stat('fairies'):
                BossSpawns.apply_modifier(BossSpawns.Faetouched, wolf)
                wolf.get_buff(CommonContent.MatureInto).spawner = mature_into
            return wolf
        evt.unit.get_buff(CommonContent.RespawnAs).spawner = modified_wolf
        if self.spell.get_stat('wmind'):
            if not any((not s.melee) and s.damage for s in evt.unit.spells):
                pounce = CommonContent.LeapAttack(damage=10, range=5)
                pounce.caster = pounce.owner = evt.unit
                pounce.cool_down = 3
                pounce.name = "Wolfstrike"
                evt.unit.spells.insert(0, pounce)


class TestingVariant(Level.Spell):
    def on_init(self):
        self.name = "Blood Moon"
        self.max_charges = 1
        self.range = 0
        self.tags = [Level.Tags.Nature, Level.Tags.Enchantment, Level.Tags.Blood]
        self.level = 7
        self.duration = 8
        self.hp_cost = 36

        self.fungus = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Lycanthrope, Monsters.FireSpirit()))

        #upgrework - finally usable as a serious spell without jank
        #fae or metal on the wolves perhaps, instead of the extra regen? clay is cool but shield regen is more useful on cowards
        #affected minions without ranged direct offense gain pouncing melee? would be neat
        #start by raising up some weremycobeasts?

        self.upgrades['fairies'] = (1, 5, "Moon-and-Star", "This spell's werewolves gain [fae:arcane].\nThis does not cause units reverting from werewolf form to gain [fae:arcane], however.")
        self.upgrades['myco'] = (1, 4, "True Bloodmoon", "Summon 6 werefire spirits when casting this spell.")
        self.upgrades['wmind'] = (1, 6, "Impart Ferocity", "Minions you summon that do not have damaging spells beyond melee range gain a pounce attack with a 5 tile range dealing 10 [physical] damage.")

    def get_description(self):
        return (
            "Whenever you would summon a non-gate minion that is not [were:dark] using a spell, except this one or [orb] spells, give it [were:dark].\n"
            "Werewolves created from affected units are unaffected by this spell.\n"
            "This effect lasts [{duration}_turns:duration]."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return self.spell_upgrades[:2] + [self.fungus()] + self.spell_upgrades[2:]

    def cast_instant(self, x, y):
        if self.get_stat('myco'):
            for _ in range(6):
                self.summon(self.fungus())
        self.caster.apply_buff(LycanthropeBuff(self), self.get_stat('duration'))

    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        return m

class MultiMove(Level.Spell):
    def on_init(self):
        self.name = "Time Skip"
        self.max_charges = 3
        self.range = 5
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane]
        self.level = 3

        self.requires_los = False
        self.can_target_empty = False

        self.upgrades['max_charges'] = (3, 2)

    def can_cast(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        return u and not Level.are_hostile(u, self.caster) and Level.Spell.can_cast(self, x, y) and any(Level.are_hostile(u, self.caster) for u in self.caster.level.units) and not u.stationary

    def get_description(self):
        return (
            "Target ally moves as many times as it can until its next action is passing the turn or casting a spell, or it moves 100 times.\n"
            "Can only be cast while at least one enemy unit is alive, and cannot be cast on immobile units."
        )

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u.is_alive():
            return
        acts_taken = 0
        while acts_taken < 100:
            if not u.is_alive() or type(u.get_ai_action()) != Level.MoveAction:
                return
            self.caster.level.leap_effect(u.x, u.y, Level.Tags.Arcane.color, u)
            u.advance()
            acts_taken += 1

class RainbowBomberBuff(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.name = "Rainbow Explosion"
        self.radius = spell.get_stat('radius')
        self.damage = spell.get_stat('minion_damage')
        self.beam_range = spell.get_stat('minion_range')

    def on_applied(self, owner):
        self.owner_triggers[Level.EventOnDeath] = self.on_death

    def on_death(self, death_event):
        self.owner.level.queue_spell(self.explode(self.owner.level, self.owner.x, self.owner.y))

    def explode(self, level, x, y):
        dtypes = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Poison, Level.Tags.Holy, Level.Tags.Dark, Level.Tags.Arcane, Level.Tags.Physical]
        dt = random.choice(dtypes)
        for point in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.radius):
            if not self.owner.level.can_see(self.owner.x, self.owner.y, point.x, point.y) and not self.spell.get_stat('penetrate'):
                continue
            self.owner.level.deal_damage(point.x, point.y, self.damage, dt, self)
        yield
        dtypes.remove(dt)
        for _ in range(1+self.spell.get_stat('double')):
            random.shuffle(dtypes)
            for d in dtypes:
                in_range = [u for u in self.owner.level.get_units_in_ball(self.owner, self.beam_range) if Level.are_hostile(self.owner, u)]
                if not self.spell.get_stat('penetrate'):
                    in_range = [u for u in in_range if u in self.owner.level.get_units_in_los(self.owner)]
                if not in_range:
                    return
                in_range.sort(key=lambda x: -x.resists[d])
                victim = in_range[0]
                base = Level.Bolt(self.owner.level, self.owner, victim, False, (not self.spell.get_stat('penetrate')))
                res = set()
                for p in base:
                    for q in self.owner.level.get_points_in_rect(p.x-1, p.y-1, p.x+1, p.y+1):
                        if self.owner.level.tiles[p.x][p.y].is_wall() and not self.spell.get_stat('penetrate'):
                            continue
                        res.add(q)
                for point in (res if self.spell.get_stat('wide') else base):
                    self.owner.level.deal_damage(point.x, point.y, self.damage, d, self)
                yield
        

class RainbowGrenade(Level.Spell):
    def on_init(self):
        self.name = "Prism Bomber"
        self.max_charges = 5
        self.range = 6
        self.tags = [Level.Tags.Arcane, Level.Tags.Conjuration]
        self.level = 4
        self.radius = 4
        self.minion_damage = 11
        self.minion_range = 10

        self.must_target_walkable = True
        self.must_target_empty = True

        self.upgrades['penetrate'] = (1, 3, "Penetrating Light", "The prism bomber's explosions can pass through walls, and its beams can target and pass through walls.")
        self.upgrades['wide'] = (1, 3, "Intensity", "The prism bomber's beams hit in a 3-tile wide line.")
        self.upgrades['double'] = (1, 5, "Double Rainbow", "The prism bomber shoots twice as many beams.")

    def get_description(self):
        return (
            "Summon the long-forgotten Prism Bomber on target tile.\n"
            "The bomber has fixed 1 HP and no resistances except an immunity to [poison], but has all damage types as tags except [physical].\n"
            "The bomber will self-destruct on death, dealing damage of a random type in a [{radius}-tile_radius:radius] and shooting 7 beams at enemies in line of sight up to [{minion_range}_tiles_away:range].\n"
            "Each beam deals damage of a unique type, except the type the bomber's explosion dealt, and will target the enemy with the lowest resistance to its type.\n"
            "The beams and explosions all deal [{minion_damage}:damage] damage."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.the_rainbow()] + self.spell_upgrades
    
    def the_rainbow(self):
        bomb = Level.Unit()
        bomb.name = "Prism Bomber"
        bomb.tags = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Poison, Level.Tags.Holy, Level.Tags.Dark, Level.Tags.Arcane]
        for dt in (bomb.tags + [Level.Tags.Physical]):
            bomb.resists[dt] = 0
        bomb.resists[Level.Tags.Poison] = 100
        bomb.max_hp = 1
        blowup = Monsters.FireBomberSuicide()
        blowup.range = self.get_stat('radius')
        blowup.description = "Suicide attack\n%d tile radius\nAutocast on death\nDeals one damage type and shoots beams that deal all other damage types" % self.get_stat('radius')
        blowup.damage = self.get_stat('minion_damage')
        blowup.damage_type = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Poison, Level.Tags.Holy, Level.Tags.Dark, Level.Tags.Arcane, Level.Tags.Physical]
        b = RainbowBomberBuff(self)
        bomb.buffs.append(b)
        bomb.spells.append(blowup)
        bomb.asset_name = "prism_bomber"
        return bomb

    def cast_instant(self, x, y):
        self.summon(self.the_rainbow(), Level.Point(x, y))

class WhiteoutBuff(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        self.damage = spell.get_stat('damage')
        Level.Buff.__init__(self)
        self.name = "Whiteout"
        self.color = Level.Tags.Ice.color
        self.owner_triggers[Level.EventOnBuffApply] = self.extend_stun
        self.buff_type = Level.BUFF_TYPE_CURSE

    def on_advance(self):
        self.owner.deal_damage(self.damage, Level.Tags.Ice, self.spell)

    def extend_stun(self, evt):
        if isinstance(evt.buff, Level.Stun) or not evt.buff.on_attempt_advance():
            evt.buff.turns_left += 4
        elif self.spell.get_stat('frail') and evt.buff.buff_type == Level.BUFF_TYPE_CURSE:
            for tag in evt.buff.resists.keys():
                if evt.buff.resists[tag] < 0:
                    self.owner.resists[tag] -= 25
                    evt.buff.resists[tag] -= 25

class Snowblind(Level.Spell):
    def on_init(self):
        self.name = "Whiteout"
        self.max_charges = 3
        self.range = 7
        self.radius = 3
        self.duration = 12
        self.damage = 3
        self.tags = [Level.Tags.Enchantment, Level.Tags.Ice]
        self.level = 4

        self.upgrades['requires_los'] = (-1, 4, "Blindcasting", "Whiteout can be cast without line of sight.")
        self.upgrades['blind'] = (1, 4, "Obscurity", "Enemies that gain Whiteout have a 25% chance to be [blinded] for half the duration, to a minimum of 1 turn.")
        self.upgrades['frail'] = (1, 3, "Bitter Cold", "If an enemy with Whiteout gains a debuff that decreases resistances, those resistances are decreased by a further 25%.")

    def get_description(self):
        return (
            "Inflict Whiteout on all enemies in a [{radius}-tile_radius:radius] for [{duration}_turns:duration].\n"
            "Whenever a unit with Whiteout gains a debuff that prevents them from acting, extend that buff's duration by a fixed 4 turns.\n"
            "Units with Whiteout also take [{damage}_ice_damage:ice] each turn."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        for v in [u for u in self.caster.level.get_units_in_ball(Level.Point(x, y), self.get_stat('radius'))]:
            if Level.are_hostile(v, self.caster):
                v.apply_buff(WhiteoutBuff(self), self.get_stat('duration'))
                if self.get_stat('blind') and random.random() < .25:
                    v.apply_buff(Level.BlindBuff(), max(1, self.get_stat('duration')//2))

class AuroraBreath(Monsters.BreathWeapon):

    def on_init(self):
        self.name = "Aurora Breath"
        self.damage = 10
        self.damage_type = [Level.Tags.Fire, Level.Tags.Ice]

    def get_description(self):
        return "Breathes a cone of hot and cold, dealing %d fire or ice damage randomly" % self.damage

    def per_square_effect(self, x, y):
        self.caster.level.deal_damage(x, y, self.damage, random.choice(self.damage_type), self)

class EssenceStack(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Soul Frostburn"
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.stack_type = Level.STACK_INTENSITY
        self.color = Level.Tags.Ice.color
                
class FurnaceBurnBuff(Level.Buff):
    def __init__(self, spell):
        self.rad = spell.get_stat('radius')
        self.spell = spell
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnDeath] = self.on_death
        self.name = "Essence Burner"
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.color = Level.Tags.Eye.color

    def update_bonuses(self):
        stacks = self.owner.get_buff_stacks(EssenceStack)
        for spell in self.owner.spells:         
            if type(spell) == AuroraBreath:
                spell.damage = self.spell.get_stat('minion_damage') + stacks//4
        frost = [b for b in self.owner.buffs if b.name == "Frostfire Aura"][0]
        frost.radius = self.rad + stacks//8
        frost.description
    
    def on_pre_advance(self):
        self.update_bonuses()
    
    def on_death(self, evt):
        if evt.unit not in self.owner.level.get_units_in_los(self.owner):
            return
        if Level.Tags.Fire not in evt.unit.tags and Level.Tags.Ice not in evt.unit.tags:
            return
        self.owner.apply_buff(EssenceStack())
        self.update_bonuses()

    def get_tooltip(self):
        return "Gains a stack of Soul Frostburn whenever a [fire] or [ice] unit dies in its line of sight. Every 4 stacks increases breath damage by 1, and every 8 stacks increases aura radius by 1."

class WeirdFurnace(Level.Spell):
    def on_init(self):
        self.name = "Frostfire Furnace"
        self.max_charges = 1
        self.melee = True
        self.range = 1.5
        self.tags = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Metallic, Level.Tags.Conjuration]
        self.level = 7
        self.radius = 6
        self.minion_health = 110
        self.minion_damage = 9
        self.minion_range = 6

        self.must_target_walkable = True
        self.must_target_empty = True

        self.upgrades['increase'] = (1, 5, "Improved Summoning", "The furnace gains an extra 10% chance to summon hounds.")
        self.upgrades['soul'] = (1, 7, "Essence Fuel", "Whenever the furnace witnesses a [fire] or [ice] unit die, it gains a stack of Soul Frostburn.\nThe furnace gains 1 ability damage for every 4 stacks, and 1 aura radius for every 8 stacks.")

    def get_description(self):
        return (
            "Summon an unusual furnace that is both hot and cold at the same time.\n"
            "This furnace is a [fire] [ice] [metallic] [construct] with [{minion_health}_HP:minion_health] and a wide array of resistances.\n"
            "The furnace has an aura dealing 1 fixed [fire] or [ice] damage to enemies in a [{radius}-tile_radius:radius] each turn.\n"
            "The furnace has a breath attack dealing [{minion_damage}:damage] [ice] or [fire] damage in a [{minion_range}-tile_cone:range].\n"
            "Each turn, the furnace has a 10% chance to summon a hellhound, and a 10% chance to summon an ice hound, which benefit from all minion bonuses except health."
        ).format(**self.fmt_dict())

    def get_extra_examine_tooltips(self):
        return [self.the_rainbow()] + self.spell_upgrades
    
    def bonus(self, u):
        CommonContent.apply_minion_bonuses(self, u)
        u.max_hp = 19
        return u
    
    def the_rainbow(self):
        bomb = Level.Unit()
        bomb.name = "Frostfire Furnace"
        bomb.asset = ["FirstMod", "walking_furnace_frostfire"]
        bomb.max_hp = self.get_stat('minion_health')
        bomb.tags = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Construct, Level.Tags.Metallic]
        bomb.resists[Level.Tags.Fire] = 100
        bomb.resists[Level.Tags.Ice] = 100
        b = CommonContent.DamageAuraBuff(damage=1, damage_type=[Level.Tags.Fire, Level.Tags.Ice], radius=self.get_stat('radius'))
        b.name = "Frostfire Aura"
        bomb.buffs.append(b)
        odds = .1 + self.get_stat('increase')/10
        bomb.buffs.extend([Monsters.GeneratorBuff(lambda: self.bonus(Monsters.HellHound()), odds), Monsters.GeneratorBuff(lambda: self.bonus(Monsters.IceHound()), odds)])
        au = AuroraBreath()
        au.cool_down = 2
        au.damage = self.get_stat('minion_damage')
        au.range = self.get_stat('minion_range')
        au.statholder = au.caster = au.owner = bomb
        bomb.spells.append(au)
        if self.get_stat('soul'):
            bomb.buffs.append(FurnaceBurnBuff(self))
        return bomb

    def cast_instant(self, x, y):
        self.summon(self.the_rainbow(), Level.Point(x, y))

class OnSummon(Level.Buff):

    def on_init(self):
        self.owner_triggers[Level.EventOnUnitAdded] = self.check_buffs
        self.buff_type = Level.BUFF_TYPE_NONE
    
    def check_buffs(self, evt):
        for b in self.owner.buffs:
            b.applied = False
            b.apply(self.owner)

class TrueSlime(Level.Spell):
    def on_init(self):
        self.name = "Goo Drop"
        self.max_charges = 1
        self.range = 6
        self.tags = [Level.Tags.Enchantment, Level.Tags.Nature, Level.Tags.Arcane]
        self.level = 7

        self.can_target_empty = False

        self.upgrades['max_charges'] = (1, 2)

    def can_cast(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        return u and not Level.are_hostile(u, self.caster) and Level.Spell.can_cast(self, x, y) and not getattr(u, "is_unique", False) and not u.has_buff(Monsters.SlimeBuff) and not Level.Tags.Undead in u.tags

    def get_description(self):
        return (
            "Target unit gains [slime] and the ability to split into slime-like versions of itself.\n"
            "The slime offshoots have all of the tags, resistances, spells, and passive effects of the unit.\n"
            "However, these slimes do not inherit any type of buff, are immobile if the target is immobile, and cannot fly.\n"
            "Cannot target unique minions, [slimes:slime], or [undead] units."
        ).format(**self.fmt_dict())
    
    def get_mutant_slime(self, max_hp, unit, name, asset):
        slime = Monsters.GreenSlime()
        slime.name = unit.name
        slime.asset = asset
        slime.max_hp = max_hp
        slime.tags = list(set(unit.tags + [Level.Tags.Slime]))
        slime.spells = copy.copy(unit.spells)
        slime.stationary = unit.stationary
        slime.outline_color = Level.Tags.Slime.color
        slime.resists = unit.resists
        for s in slime.spells:
            s.statholder = slime
            s.owner = slime
            s.caster = slime
        slime.buffs[0] = Monsters.SlimeBuff(lambda: self.get_mutant_slime(max_hp, unit, name, asset), name)
        slime.buffs.append(OnSummon())
        for b in slime.buffs:
            b.owner = slime
            b.applied = False
        slime.source = self
        return slime

    def cast_instant(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        name = u.name.lower() + "s"
        asset = ['char', u.get_asset_name()] if not u.asset else u.asset
        b = Monsters.SlimeBuff(lambda: self.get_mutant_slime(u.max_hp, u, name, asset), name)
        b.buff_type = Level.BUFF_TYPE_PASSIVE
        u.apply_buff(b)
        u.tags = list(set(u.tags + [Level.Tags.Slime]))
        u.outline_color = Level.Tags.Slime.color

class DarkSlime(Level.Spell):
    def on_init(self):
        self.name = "Black Pudding"
        self.max_charges = 3
        self.range = 5
        self.tags = [Level.Tags.Conjuration, Level.Tags.Dark, Level.Tags.Nature]
        self.level = 3
        self.minion_health = 20
        self.minion_damage = 3
        self.num_summons = 1 #black horde bad

        self.must_target_empty = True
        self.must_target_walkable = True

        self.upgrades['db'] = (1, 6, "Arcanist's Dessert", "The pudding can cast your Death Bolt with a 9 turn cooldown.")
        self.upgrades['necro'] = (1, 4, "Ghost Pudding", "Puddings gain ghostly.")
        self.upgrades['num_summons'] = (1, 3, "Black Horde")

    def get_description(self):
        return (
            "Summon a black pudding on target tile."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.pudding()] + self.spell_upgrades

    def pudding(self):
        mon = Level.Unit()
        mon.asset = ["FirstMod", "black_slime"]
        mon.name = "Black Pudding"
        mon.tags = [Level.Tags.Dark, Level.Tags.Slime]
        mon.max_hp = self.get_stat('minion_health')
        mon.resists[Level.Tags.Dark] = 100
        mon.resists[Level.Tags.Physical] += 50
        mon.resists[Level.Tags.Holy] = 0
        mon.spells.append(CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage'), damage_type=Level.Tags.Dark))
        mon.buffs.append(Monsters.SlimeBuff(self.pudding, "black puddings"))
        if self.get_stat('necro'):
            BossSpawns.apply_modifier(BossSpawns.Ghostly, mon)
            mon.resists[Level.Tags.Physical] = 100
        if self.get_stat('db'):
            db = Spells.DeathBolt()
            db.caster = mon
            db.statholder = self.caster
            db.owner = mon
            db.cool_down = 9
            mon.spells.insert(0, db)
        return mon

    def cast_instant(self, x, y):
        for _ in range(self.get_stat('num_summons')):
            self.summon(self.pudding(), Level.Point(x, y))  

class CallAncient(Level.Spell):

    def on_init(self):

        self.name = "Call Ancestor"
        self.max_charges = 0
        self.range = 5
        self.tags = [Level.Tags.Conjuration, Level.Tags.Arcane, Level.Tags.Dark]
        self.level = 5
        self.max_charges = 3
        self.must_target_walkable = True
        self.must_target_empty = True
        self.minion_health = 66
        self.minion_damage = 10
        self.minion_range = 6
        self.shields = 3

        self.upgrades['megapull'] = (2, 4, "Enhanced Pull", "The Ancestor's pull attack moves targets an extra 2 tiles.")
        self.upgrades['extrahit'] = (2, 4, "Ferocity", "The Ancestor's melee hits an extra 2 times.", "melee")
        self.upgrades['mind'] = (1, 6, "Void Mind", "On hit, the Ancestor's melee randomly summons rot and insanity imps near the target, with two imps being summoned per hit.", "melee")

    def get_description(self):
        return (
            "Summon the Ancestor, an [arcane] [living] [demon] minion with [{minion_health}_HP:minion_health] and [{shields}_SH:shield].\n"
            "The Ancestor takes double damage from [holy] and [poison] but is immune to [arcane] and [dark].\n"
            "It also has a melee attack dealing [{minion_damage}:damage] [arcane] damage, which hits twice and heals the Ancestor for the damage dealt.\n"
            "The Ancestor can also pull enemies in [{minion_range}_tiles:range] 1 tile towards itself while dealing a fixed 4 [dark] damage to them.\n"
            "The Ancestor will prefer to use its melee attack wherever possible."
            ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.make_siege()] + self.spell_upgrades
    
    def make_siege(self):
        walker = Level.Unit()
        walker.max_hp = self.get_stat('minion_health')
        walker.name = "Ancestor"
        walker.asset_name = "demo1"
        walker.tags = [Level.Tags.Living, Level.Tags.Arcane, Level.Tags.Demon]
        walker.resists[Level.Tags.Poison] = -100
        walker.resists[Level.Tags.Holy] = -100
        walker.resists[Level.Tags.Arcane] = 100
        walker.resists[Level.Tags.Dark] = 100
        walker.shields = self.get_stat('shields')
        pullin = CommonContent.PullAttack(damage=4, damage_type=Level.Tags.Dark, range=self.get_stat('minion_range'), pull_squares=1+self.get_stat('megapull'), color=Level.Tags.Tongue.color)
        pullin.name = "Primordial Pull"
        melee = CommonContent.SimpleMeleeAttack(damage=self.get_stat('minion_damage'), damage_type=Level.Tags.Arcane, attacks=2+self.get_stat('extrahit'), drain=True)
        melee.name = "Ancient Bite"
        if self.get_stat('mind'):
            def mind_onhit(c, t):
                for _ in range(2):
                    mon = random.choice([Monsters.InsanityImp(), Monsters.RotImp()])
                    p = c.level.get_summon_point(t.x, t.y, 6)
                    if p:
                        c.level.summon(c, mon, p)
            melee.onhit = mind_onhit
            melee.description  = melee.get_description() + " Summons rot and insanity imps on hit"
        walker.spells = [melee, pullin]
        return walker
    
    def cast_instant(self, x, y):
        self.summon(self.make_siege(), Level.Point(x, y))

class GenericResummon(Level.Buff):
    def __init__(self, times):
        self.times = times
        self.activated = False
        Level.Buff.__init__(self)
        self.name = "Resummon"
        self.color = Level.Tags.Holy.color
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.owner_triggers[Level.EventOnUnitAdded] = self.resummon
    
    def resummon(self, evt):
        if not self.activated:
            self.activated = True
            for _ in range(self.times):
                self.owner.level.event_manager.raise_event(Level.EventOnUnitAdded(self.owner), self.owner)
    
    def get_tooltip(self):
        return "On being summoned, pretends to resummon self an extra %d times" % self.times
    
class PreserveBuff(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Preservation"
        self.color = Level.Tags.Holy.color
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.global_triggers[Level.EventOnSpellCast] = self.on_cast
    
    def on_cast(self, evt):
        hp_gain = evt.spell.level
        if (Level.Tags.Holy in evt.spell.tags 
            and evt.caster.is_player_controlled 
            and self.owner.level.can_see(self.owner.x, self.owner.y, evt.x, evt.y)):
            self.owner.max_hp += hp_gain
            self.owner.cur_hp += hp_gain
            self.owner.level.queue_spell(self.effect(evt.x, evt.y))


    def effect(self, x, y):
        for p in self.owner.level.get_points_in_line(Level.Point(x, y), self.owner, find_clear=True):
            self.owner.level.flash(p.x, p.y, Level.Tags.Holy.color)
            yield
        self.owner.level.flash(self.owner.x, self.owner.y, Level.Tags.Heal.color)

    def get_tooltip(self):
        return "Gains max and current HP equal to the spell's level when witnessing a holy spell"

class Slimefuls(Upgrades.Upgrade):
    def on_init(self):
        self.prereq = LightSlime
        self.name = "Slimefuls for All"
        self.level = 6
        self.description = "On the third turn after entering a new realm, cast this spell near each [living] ally, [demon] enemy, and [undead] enemy in a 4 tile radius, if possible."

    def is_valid(self, u):
        if u.is_player_controlled:
            return False
        if Level.Tags.Living in u.tags and not Level.are_hostile(u, self.owner):
            return True
        elif (Level.Tags.Demon in u.tags or Level.Tags.Undead in u.tags) and Level.are_hostile(u, self.owner):
            return True
        else:
            return False
        
    def on_advance(self):
        if self.owner.level.turn_no == 3:
            slime = [s for s in self.owner.spells if isinstance(s, LightSlime)]
            if not slime:
                return
            slime = slime[0]
            victims = [u for u in self.owner.level.get_units_in_ball(self.owner, 4) if self.is_valid(u)]
            if not victims:
                return
            for v in victims:
                self.owner.level.act_cast(self.owner, slime, v.x, v.y, False)

class LightSlime(Level.Spell):
    def on_init(self):
        self.name = "Light Flan"
        self.max_charges = 3
        self.range = 5
        self.tags = [Level.Tags.Conjuration, Level.Tags.Holy]
        self.level = 3
        self.minion_health = 20
        self.minion_damage = 4

        self.must_target_empty = True
        self.must_target_walkable = True

        self.upgrades['gold'] = (1, 5, "Gold-Crusted Flan", "Flans gain 50 [fire], [ice], and [lightning] resist.")
        self.upgrades['spell'] = (1, 6, "Spell Preservative", "Whenever a flan sees you cast a [holy] spell, it gains max HP and heals for an amount equal to the spell's level.")
        self.upgrades['mirage'] = (1, 3, "Mirage Light", "Flans benefit twice from most on-summon effects.")
        self.add_upgrade(Slimefuls())

    def get_description(self):
        return (
            "Summon a light flan on target tile.\n"
            "The flan is a [holy] [slime] with [{minion_health}_HP:minion_health], immunity to [holy] and [poison], and 50 [physical] resist. However, the flan takes double [dark] damage.\n"
            "The pudding has a melee attack dealing [{minion_damage}_holy_damage:holy]."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.pudding()] + self.spell_upgrades

    def pudding(self):
        mon = Level.Unit()
        mon.asset = ["FirstMod", "holy_slime"]
        mon.name = "Light Flan"
        mon.tags = [Level.Tags.Holy, Level.Tags.Slime]
        mon.max_hp = self.get_stat('minion_health')
        mon.resists[Level.Tags.Dark] = -100
        mon.resists[Level.Tags.Physical] = 50
        mon.resists[Level.Tags.Holy] = 100
        if self.get_stat('gold'):
            for t in [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning]:
                mon.resists[t] = 50
        if self.get_stat('mirage'):
            mon.buffs.append(GenericResummon(1))
        if self.get_stat('spell'):
            mon.buffs.append(PreserveBuff())
        mon.spells.append(CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage'), damage_type=Level.Tags.Holy))
        mon.buffs.append(Monsters.SlimeBuff(self.pudding, "light flans"))
        return mon

    def cast_instant(self, x, y):
        self.summon(self.pudding(), Level.Point(x, y))  

class HealRemoval(Level.Buff):
    def on_init(self):
        self.name = "Heal Removal"
        self.resists[Level.Tags.Heal] = 100
        self.color = Level.Tags.Poison.color
        self.buff_type = Level.BUFF_TYPE_CURSE
                
class SplitBooster(Level.Buff):
    def __init__(self, quant):
        self.quant = quant
        Level.Buff.__init__(self)
        self.color = Level.Tags.Slime.color
        self.buff_type = Level.BUFF_TYPE_PASSIVE

    def on_advance(self):
        b = self.owner.get_buff(Monsters.SlimeBuff)
        if b:
            for _ in range(self.quant):
                b.on_advance()
    
    def get_tooltip(self):
        return "Slime buff activates an extra %d times every turn" % self.quant
    
class SugaryBlood(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Sugary Blood"
        self.color = Level.Tags.Demon.color
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.owner_triggers[Level.EventOnPreDamaged] = self.raise_max
        self.owner_triggers[Level.EventOnDamaged] = self.queue_split

    def raise_max(self, evt):
        if evt.damage > 0 or evt.damage_type != Level.Tags.Heal or isinstance(evt.source, Monsters.SlimeBuff):
            return
        self.owner.max_hp -= evt.damage

    def queue_split(self, evt):
        if evt.damage > 0 or evt.damage_type != Level.Tags.Heal or random.random() < .5:
            return
        b = self.owner.get_buff(Monsters.SlimeBuff)
        if b:
            b.on_advance()

    def get_tooltip(self):
        return "Whenever this unit is about to be healed, gains that much max HP first, then has a 50% chance to try and split after being healed."      

class BloodySlime(Level.Spell):
    def on_init(self):
        self.name = "Expunging Ritual"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Blood, Level.Tags.Conjuration]
        self.level = 4
        self.minion_health = 10
        self.minion_damage = 3
        self.max_channel = 4
        self.hp_cost = 40
        self.times = 0

        self.upgrades['end'] = (1, 6, "To the Very Last", "Instead of sacrificing 40 HP, sacrifice all but 1 of your HP, but you can still only cast Expunging Ritual if your HP is above 40.\nFor every 20 extra HP you sacrificed, rounded down, the on-turn effect of the slimes' splitting buff activates one extra time.", "bloody")
        self.upgrades['sugary'] = (1, 5, "Sugared Blood", "Whenever a blood slime would be healed by a source other than its slime growth, it gains that much max HP first, then it has a 50% chance to attempt to split.", "bloody")

    def get_description(self):
        return (
            "Sacrifice some HP and channel this spell for 4 turns. After channeling, gain 100 [heal] resist for 2 turns, then summon 8 blood slimes near yourself.\n"
            "Each one is a [demon] [slime] with [{minion_health}_HP:minion_health] and an immunity to [dark] and [poison]. The slimes also take half [physical] damage and double [holy] damage.\n" 
            "Blood slimes have melee attacks that deal [{minion_damage}_dark_damage:dark] while healing them for the damage dealt and granting them +1 damage for 10 turns."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.pudding()] + self.spell_upgrades

    def pudding(self, boost=0):
        mon = Level.Unit()
        mon.asset = ["FirstMod", "blood_slime"]
        mon.name = "Blood Slime"
        mon.tags = [Level.Tags.Demon, Level.Tags.Slime]
        mon.max_hp = self.get_stat('minion_health')
        mon.resists[Level.Tags.Dark] = 100
        mon.resists[Level.Tags.Poison] = 100
        mon.resists[Level.Tags.Physical] = 50
        mon.resists[Level.Tags.Holy] = -100
        m = CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage'), damage_type=Level.Tags.Dark, onhit=CommonContent.bloodrage(1), drain=True)
        m.description = "Drains life.\nGains 1 damage for 10 turns on hit."
        mon.spells.append(m)
        mon.buffs.append(Monsters.SlimeBuff(lambda: self.pudding(boost)))
        if boost > 0:
            mon.buffs.append(SplitBooster(boost))
        if self.get_stat('sugary'):
            mon.buffs.append(SugaryBlood())
        return mon

    def cast(self, x, y, channel_cast=False):
        if not channel_cast:
            if self.get_stat('end'):
                self.times = (self.caster.cur_hp - 1) // 20
                self.caster.level.event_manager.raise_event(Level.EventOnSpendHP(self.caster, self.caster.cur_hp-1), self.caster)
                self.caster.cur_hp = 1
            self.caster.apply_buff(Level.ChannelBuff(self.cast, Level.Point(x, y)), self.get_stat('max_channel'))
            return
        yield

        if not self.caster.has_buff(Level.ChannelBuff):
            for _ in range(8):
                p = self.pudding(self.times)
                self.summon(p, radius=7)
                yield
            self.caster.apply_buff(HealRemoval(), 2)
            

class Dummy(Level.Spell):

    def on_init(self):

        self.name = "Dummy"
        self.max_charges = 0
        self.range = Level.RANGE_GLOBAL
        self.tags = [Level.Tags.Conjuration]
        self.level = 1
        self.must_target_walkable = True
        self.must_target_empty = True
        self.requires_los = False

        self.upgrades['enemy'] = (1, 0, "Enemy", "Make an enemy dummy instead.")

    def get_description(self):
        return (
            "Permanent training dummy for testing purposes."
            ).format(**self.fmt_dict())
    
    def make_siege(self):
        walker = RareMonsters.FlyTrap()
        walker.max_hp = 100000
        walker.spells.clear()
        return walker
    
    def cast_instant(self, x, y):
        dum = self.make_siege()
        self.summon(dum, Level.Point(x, y))
        if self.get_stat('enemy'):
            dum.team = Level.TEAM_ENEMY

class DummyBone(Level.Spell):

    def on_init(self):

        self.name = "John's Experiment"
        self.max_charges = 0
        self.range = Level.RANGE_GLOBAL
        self.tags = [Level.Tags.Conjuration]
        self.level = 1
        self.must_target_walkable = True
        self.must_target_empty = True
        self.requires_los = False

        self.upgrades['enemy'] = (1, 0, "Enemy", "Make an enemy megalith instead.")

    def get_description(self):
        return (
            "Permanent immortal bone shambler megalith for testing purposes."
            ).format(**self.fmt_dict())
    
    def make_siege(self):
        walker = BossSpawns.apply_modifier(BossSpawns.Immortal, Monsters.BoneShambler(256))
        walker.spells.clear()
        return walker
    
    def cast_instant(self, x, y):
        dum = self.make_siege()
        self.summon(dum, Level.Point(x, y))
        if self.get_stat('enemy'):
            dum.team = Level.TEAM_ENEMY

class WizSwap(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.color = Level.Tags.Arcane.color
        self.name = "Magic Swap"
        self.oldspells = None

    def on_applied(self, owner):
        self.oldspells = owner.spells
        valids = [RareMonsters.IceWizard().spells, RareMonsters.FireWizard().spells, RareMonsters.LightningWizard().spells]
        if self.spell.get_stat('enchanter'):
            valids.append(RareMonsters.Enchanter().spells)
        if self.spell.get_stat('bone'):
            valids.append(Monsters.BoneWizard().spells)
        if self.spell.get_stat('void'):
            valids.append(RareMonsters.VoidWizard().spells)
        slist = random.choice(valids)
        for s in slist:
            s.cool_down = 0
            s.owner = self.owner
            s.caster = self.owner
            s.statholder = self.owner
            s.tags = []
        owner.spells = slist

    def on_unapplied(self):
        self.owner.spells = self.oldspells

class MageMoves(Level.Spell):
    def on_init(self):
        self.name = "Exchange Arcana"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane]
        self.level = 6
        self.duration = 22
        
        self.upgrades['enchanter'] = (1, 6, "Enchanting Exchange", "Exchange Arcana can also grant the moveset of an Enchanter.", "exchange")
        self.upgrades['bone'] = (1, 6, "Decaying Exchange", "Exchange Arcana can also grant the moveset of a Bone Wizard.", "exchange")
        self.upgrades['void'] = (1, 6, "Mystic Exchange", "Exchange Arcana can also grant the moveset of a Void Magus.", "exchange")

    def get_description(self):
        return (
            "Randomly assume the moveset of either a Lightning Master, Ice Wizard, or Fire Wizard for [{duration}_turns:duration].\n"
            "These spells have no cooldowns, but do not benefit from any of your bonuses.\n"
            "You cannot cast your other spells while this effect is active."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.owner.apply_buff(WizSwap(self), self.get_stat('duration'))

class Tension(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnDamaged] = self.on_damage
        self.color = Level.Tags.Arcane.color
        self.name = "Tension"
        self.global_bonuses_pct['damage'] = 20
        self.stack_type = Level.STACK_INTENSITY

    def on_damage(self, evt):
        if evt.source == self.owner or evt.source.owner == self.owner:
            self.owner.remove_buff(self)

class TensionTest(Level.Spell):
    def on_init(self):
        self.name = "Psyche Up"
        self.max_charges = 12
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane]
        self.level = 2

        self.upgrades['max_charges'] = (10, 3)
        self.upgrades['double'] = (1, 5, "Super Focus", "Psyche Up gives two stacks of tension instead of one.")

    def get_description(self):
        return (
            "Gain one stack of tension, which increases the damage of the Wizard's next spell or skill activation by 20%. All stacks of tension will be removed when the Wizard deals damage."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        for _ in range(1+self.get_stat('double')):
            self.owner.apply_buff(Tension())

class TensionDance(Level.Spell):
    def on_init(self):
        self.name = "Jester's Jig"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane]
        self.level = 4

    def can_cast(self, x, y):
        return Level.Spell.can_cast(self, x, y) and self.caster.get_buff_stacks(Tension) >= 2

    def get_description(self):
        return (
            "The wizard loses two stacks of tension, then all allies in line of sight gain one stack of tension."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        to_reapply = self.caster.get_buff_stacks(Tension)-2
        self.caster.level.event_manager.raise_event(Level.EventOnDamaged(self.caster, 0, Level.Tags.Fire, self), self.caster)
        allies = [u for u in self.caster.level.get_units_in_los(self.caster) if not Level.are_hostile(u, self.owner) and u != self.owner]
        for a in allies:
            a.apply_buff(Tension())
        for _ in range(to_reapply):
            self.caster.apply_buff(Tension())

class GiantAxe(Level.Spell):
    def on_init(self):
        self.name = "Giant Axe"
        self.max_charges = 15
        self.range = 5
        self.tags = [Level.Tags.Metallic, Level.Tags.Sorcery]
        self.level = 3
        self.damage = 70

        self.upgrades['long'] = (1, 3, "Extendable Handle", "Giant Axe can also be used on tiles 3 tiles away from the Wizard.")
        self.upgrades['crush'] = (1, 4, "Crushing Blow", "Giant Axe destroys wall tiles in a 2-tile radius around the target point.\nThe axe has a 20% chance to critically strike against targets not immune to [physical], dealing damage an extra 2 times.")
        self.upgrades['antighost'] = (1, 3, "Phantom Cleaver", "If the target is immune to [physical] damage, Giant Axe deals [dark] and [holy] damage to the target and [stuns] them for 1 turn.")

    def can_cast(self, x, y):
        dists = [2]
        if self.get_stat('long'):
            dists.append(3)
        return Level.Spell.can_cast(self, x, y) and Level.distance(self.caster, Level.Point(x, y), diag=True) in dists

    def get_description(self):
        return (
            "Swing with a massive axe, dealing [{damage}_physical_damage:physical] to the target. Can only be used on tiles 2 tiles away from the Wizard."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if u and u.resists[Level.Tags.Physical] >= 100 and self.get_stat('antighost'):
            u.deal_damage(self.get_stat('damage'), Level.Tags.Dark, self)
            u.deal_damage(self.get_stat('damage'), Level.Tags.Holy, self)
            u.apply_buff(Level.Stun(), 1)
        else:
            self.caster.level.deal_damage(x, y, self.get_stat('damage'), Level.Tags.Physical, self)
            if self.get_stat('crush') and random.random() < .2 and u and u.resists[Level.Tags.Physical] < 100:
                for _ in range(2):
                    u.deal_damage(self.get_stat('damage'), Level.Tags.Physical, self)
        if self.get_stat('crush'):
            for p in self.caster.level.get_points_in_ball(x, y, 2):
                if self.caster.level.tiles[p.x][p.y].is_wall():
                    self.owner.level.make_floor(p.x, p.y)
                    self.owner.level.show_effect(p.x, p.y, Level.Tags.Physical)

class SwordCurse(Level.Spell):
    def on_init(self):
        self.name = "Cursed Cabers"
        self.max_charges = 4
        self.range = 6
        self.tags = [Level.Tags.Metallic, Level.Tags.Sorcery, Level.Tags.Dark]
        self.level = 4
        self.damage = 3
        self.num_targets = 5
        self.can_target_empty = False

        self.upgrades['spellbane'] = (1, 7, "Imprison Magic", "Each sword also increases all of the target's spell cooldowns by 1, but this does not work on spells with no cooldown.", "cursing")
        self.upgrades['siphon'] = (1, 4, "Force Funnel", "Whenever the swords drain max HP, gain one stack of Vitality, which increases minion health of all spells and skills by 1 for 4 turns.", "cursing")
        self.upgrades['universal'] = (1, 5, "Greater Bane", "The swords can drain max HP from [demon] and [undead] units, and drain twice as much from [living] and [nature] units.", "cursing")

    def get_description(self):
        return (
            "[{num_targets}:num_targets] cursed swords pierce the target, dealing [{damage}:damage] [physical] and [dark] damage each.\n"
            "Each sword also reduces the target's max HP by a fixed 1 point if it is not an [undead] or [demon]."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        for _ in range(self.get_stat('num_targets')):
            if not u.is_alive():
                break
            for d in [Level.Tags.Dark, Level.Tags.Physical]:
                u.deal_damage(self.get_stat('damage'), d, self)
            if (Level.Tags.Undead not in u.tags and Level.Tags.Demon not in u.tags) or self.get_stat('universal'):
                mod = int((Level.Tags.Living in u.tags or Level.Tags.Nature in u.tags) and self.get_stat('universal'))
                u.max_hp = max(1+mod, u.max_hp-1)
                if self.get_stat('siphon'):
                    vitality = Level.Buff()
                    vitality.color = Level.Tags.Demon.color
                    vitality.name = "Vitality"
                    vitality.global_bonuses['minion_health'] = 1
                    vitality.stack_type = Level.STACK_INTENSITY
                    vitality.buff_type = Level.BUFF_TYPE_BLESS
                    self.caster.apply_buff(vitality, 4)
            if self.get_stat('spellbane'):
                for s in u.spells:
                    if s.cool_down > 0:
                        s.cool_down += 1    

class RealCoven(Level.Spell):
    def on_init(self):
        self.name = "Dark Sisterhood"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Conjuration, Level.Tags.Dark]
        self.level = 4
        self.num_summons = 3

        ex = Monsters.Witch()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[1].damage
        self.minion_range = ex.spells[1].range

        self.witch = lambda: self.sourceify(Monsters.Witch())
        self.oldblood_witch = lambda: self.sourceify(Monsters.OldBloodWitch())
        self.chaos_witch = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Claytouched, BossSpawns.apply_modifier(BossSpawns.Chaostouched, Monsters.Witch())))
        self.fire_witch = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Flametouched, Monsters.Witch()))

        #upgrework? this shit is kinda lame right now but it is also really damn good once you set it up
        #increase level but give it more powerful upgrades?
        #one upgrade for old blood witches, others probably variants, we do have night hag
        #chaos witches? they dont have the hp to spawn that many imps but the ranged attack is rather good
        #witches gain a healing ability?
        #nah, fuck it, burning witches

        self.upgrades['blooders'] = (1, 5, "Coven of the First Blood", "Summon old blood witches instead of normal ones.")
        self.upgrades['chaos_w'] = (1, 7, "Coven of the Mad Earth", "Summon [clay:physical] [chaos] witches instead of normal ones.")
        self.upgrades['burning'] = (1, 6, "Coven of the Last Flame", "Summon [burning:fire] witches instead of normal ones.")

    def get_description(self):
        return (
            "Summon a coven of [{num_summons}:num_summons] witches near yourself.\n"
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.witch(),
                self.spell_upgrades[0],
                self.oldblood_witch(),
                self.spell_upgrades[1],
                self.chaos_witch(),
                self.spell_upgrades[2],
                self.fire_witch()
                ]
    
    def sourceify(self, m):
        CommonContent.apply_minion_bonuses(self, m)
        return m

    def cast_instant(self, x, y):
        for _ in range(self.get_stat('num_summons')):
            m = self.witch()
            if self.get_stat('blooders'):
                m = self.oldblood_witch()
            elif self.get_stat('chaos_w'):
                m = self.chaos_witch()
                m.buffs[0].num_spawns = min(max(m.max_hp//15 + 1, 1), 10)
                m.buffs[0].description = "On death, spawns %d imps" % m.buffs[0].num_spawns
            elif self.get_stat('burning'):
                m = self.fire_witch()
            self.summon(m, self.caster)
    
class WizardDemonicPromotionCustom(Level.Spell):

    def on_init(self):
        self.name = "Demonic Promotion"
        self.description = "Transforms an imp into a fiend"
        self.range = 10
        self.cool_down = 30
        self.target_allies = True
        self.fiend_table = {
            'Fire Imp': Monsters.RedFiend,
            'Spark Imp': Monsters.YellowFiend,
            'Iron Imp': Monsters.IronFiend,
            'Ash Imp': Monsters.AshFiend,
            'Copper Imp': Monsters.CopperFiend,
            'Furnace Imp': Monsters.FurnaceFiend,
            'Chaos Imp': Monsters.ChaosFiend,
            'Insanity Imp': Monsters.InsanityFiend,
            'Rot Imp': Monsters.RotFiend
        }

    def can_cast(self, x, y):
        unit = self.owner.level.get_unit_at(x, y)
        if not unit:
            return
        if unit.name not in self.fiend_table.keys():
            return False
        return Level.Spell.can_cast(self, x, y)

    def cast_instant(self, x, y):
        unit = self.owner.level.get_unit_at(x, y)
        if not unit:
            return
        if unit.name not in self.fiend_table.keys():
            return
        
        unit.kill(trigger_death_event=False)

        fiend = self.fiend_table[unit.name]()
        if fiend:
            self.summon(fiend, target=Level.Point(unit.x, unit.y))

class Warlock(Level.Spell):
    def on_init(self):
        self.name = "Conjure Warlock"
        self.max_charges = 1
        self.range = 5
        self.tags = [Level.Tags.Conjuration, Level.Tags.Dark, Level.Tags.Chaos]
        self.level = 7
        self.must_target_walkable = True
        self.must_target_empty = True

        ex = RareMonsters.ChaosWizard()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[2].damage
        self.minion_range = ex.spells[2].range

        self.upgrades['quick'] = (1, 5, "Quick Promotion", "The warlock's promotion ability has 10 less cooldown.")

    def can_cast(self, x, y):
        return Level.Spell.can_cast(self, x, y) and not any(u.source == self for u in self.caster.level.units)
    
    def get_extra_examine_tooltips(self):
        return [self.wiz()] + self.spell_upgrades

    def get_description(self):
        return (
            "Summon a grand warlock near yourself.\n"
            "The grand warlock has [{minion_health}_HP:minion_health] and a variety of resistances and abilities.\n"
            "You may only summon one warlock at a time."
        ).format(**self.fmt_dict())
    
    def wiz(self):
        m = RareMonsters.ChaosWizard()
        CommonContent.apply_minion_bonuses(self, m)
        m.spells[1] = WizardDemonicPromotionCustom()
        if self.get_stat('quick'):
            m.spells[1].cool_down -= 10
        return m

    def cast_instant(self, x, y):
        self.summon(self.wiz(), Level.Point(x, y))

class UniversalRageBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnDeath] = self.on_death
        self.color = Level.Tags.Blood.color
        self.name = "Bloody Feast"
    
    def on_death(self, evt):
        invalid_tags = [Level.Tags.Undead, Level.Tags.Construct]
        if Level.Tags.Living not in evt.unit.tags or not Level.are_hostile(evt.unit, self.owner):
            return
        allies = [u for u in self.owner.level.get_units_in_los(evt.unit)] 
        eligibles = [u for u in allies if not Level.are_hostile(u, self.owner) and not any(t in evt.unit.tags for t in invalid_tags) and u != self.owner]
        if not eligibles:
            return
        for a in eligibles:
            dur = self.spell.get_stat('duration') // 2 - 1
            if dur <= 0:
                return
            a.apply_buff(CommonContent.BloodrageBuff(2), dur)
            if self.spell.get_stat('invigorate') and evt.unit.max_hp >= 80:
                eligibles = dict([s for s in a.cool_downs.items() if s[1] > 1])
                if not eligibles:
                    return
                max_cd = max(eligibles, key=lambda x: a.cool_downs[x])
                a.cool_downs[max_cd] -= 1
            elif self.spell.get_stat('hardy') and evt.unit.max_hp >= 60:
                for b in a.buffs:
                    if b.buff_type == Level.BUFF_TYPE_CURSE:
                        a.remove_buff(b)
            
class RAGING(Level.Spell):
    def on_init(self):
        self.name = "Blood Feast"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Blood, Level.Tags.Nature]
        self.level = 5
        self.hp_cost = 33
        self.duration = 13

        self.upgrades['invigorate'] = (1, 5, "Invigorating Meal", "If a [living] enemy with 80 or more max HP dies, all allies in line of sight of it have their highest ability cooldown decreased by 1.")
        self.upgrades['hardy'] = (1, 5, "Banquet of Respite", "If a [living] enemy with 60 or more max HP dies, all allies in line of sight of it are cleansed of debuffs, including [poison].")
        self.upgrades['duration'] = (8, 6)

    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['blood_dur'] = max(3, (d['duration'] // 2) - 1)
        return d

    def get_description(self):
        return (
            "For [{duration}_turns:duration], when a [living] enemy dies, all allies in line of sight of it gain [bloodrage:demon] for [{blood_dur}_turns:duration].\n"
            "This bloodrage increases damage by 2.\n"
            "[Undead] and [construct] allies are unaffected."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.caster.apply_buff(UniversalRageBuff(self), self.get_stat('duration'))

class MoonCrash(Level.Spell):
    def on_init(self):
        self.name = "Lunar Crash"
        self.max_charges = 1
        self.range = 13
        self.tags = [Level.Tags.Arcane, Level.Tags.Sorcery, Level.Tags.Enchantment, Level.Tags.Conjuration]
        self.level = 7
        self.damage = 31
        self.requires_los = False
        self.radius = 4
        self.duration = 7

        ex = Monsters.Lamasu()
        self.minion_range = ex.spells[1].range
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        self.upgrades['d'] = (1, 7, "Black Luna", "Enemies take an additional 25% of this spell's damage as [dark] damage. Summon a lamasu lich instead of a lamasu.")
        self.upgrades['a'] = (1, 7, "Astral Tidings", "Summon a moon mage with fixed 55 HP and 5 SH instead of a lamasu.")

    def get_description(self):
        return (
            "Throw an ancient moon down from the sky, crashing in a [{radius}-tile_radius:radius].\n"
            "All walls in the area are destroyed, and all units in the radius take [{damage}_arcane_damage:arcane].\n"
            "Enemies in the area are inflicted with Lunar Peace before taking damage, reducing all their spell damage by half for [{duration}_turns:duration].\n"
            "Summon a lamasu at the center tile.\n"
            "The lamasu is a [living] [nature] [holy] unit with [{minion_health}_HP:minion_health], [3_SH:shield], and a melee attack dealig [{minion_damage}_physical_damage:physical].\n"
            "The lamasu also has a charge attack with a [{minion_range}-tile_range:range], and heals allies in a 6-tile radius for 5 HP each turn."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.lamasu(),
                self.spell_upgrades[0],
                self.lamasu(True),
                self.spell_upgrades[1],
                self.moonmage()
                ]
    
    def lamasu(self, lich=False):
        lama = Monsters.Lamasu() if not lich else BossSpawns.apply_modifier(BossSpawns.Lich, Monsters.Lamasu())
        CommonContent.apply_minion_bonuses(self, lama)
        lama.max_hp = self.get_stat('minion_health')
        lama.shields = 3
        return lama
    
    def moonmage(self):
        lama = RareMonsters.MoonMage()
        CommonContent.apply_minion_bonuses(self, lama)
        lama.max_hp = 55
        lama.shields = 5
        return lama

    def cast_instant(self, x, y):
        for p in self.caster.level.get_points_in_ball(x, y, self.get_stat('radius')):
            if self.owner.level.tiles[p.x][p.y].is_wall():
                self.owner.level.make_floor(p.x, p.y)
            u = self.owner.level.get_unit_at(p.x, p.y)
            if u and Level.are_hostile(u, self.owner):
                LP = Level.Buff()
                LP.color = Level.Tags.Arcane.color
                LP.global_bonuses_pct["damage"] = -50
                LP.name = "Lunar Peace"
                LP.buff_type = Level.BUFF_TYPE_CURSE
                u.apply_buff(LP, self.get_stat('duration'))
                if self.get_stat('d'):
                    u.deal_damage(self.get_stat('damage')//4, Level.Tags.Dark, self)
            self.owner.level.deal_damage(p.x, p.y, self.get_stat('damage'), Level.Tags.Arcane, self)
        m = self.lamasu(bool(self.get_stat('d'))) if not self.get_stat('a') else self.moonmage()
        self.summon(m, Level.Point(x, y))

#the mmx references
#magma blade: deal phy+fire in 2-range seraph swing
#strikechain: deal phy, grapple towards walls and pick up consumables
#goo shaver: drop ice blocks in two cones in front of and behind the player, 2x benefits from num targets


class MagmaSword(Level.Spell):
    def on_init(self):
        self.name = "Magma Blade"
        self.max_charges = 3
        self.tags = [Level.Tags.Fire, Level.Tags.Nature, Level.Tags.Sorcery]
        self.melee = True
        self.range = 1.5
        self.level = 5
        self.damage = 17

        self.upgrades['dw'] = (1, 5, "Dual Wield", "Magma Blade deals damage twice.")
        self.upgrades['acid'] = (1, 4, "Caustic Sword", "Magma Blade deals an extra hit of [poison] damage.\nHit units lose [poison] resistance by 100 for 10 turns.\nThis stacks with other effects that reduce [poison] resistance.")
    
    def get_impacted_tiles(self, x, y):
        ball = self.caster.level.get_points_in_ball(x, y, 2)
        aoe = [p for p in ball if 1 <= Level.distance(p, self.caster, diag=True) < 2.5]
        return aoe

    def get_description(self):
        return (
            "Slash with a blade of pure magma, dealing [{damage}:damage] [fire] and [physical] damage.\n"
            "The blade affects an arc extending a fixed 2 tiles away."
        ).format(**self.fmt_dict())
    
    def cast(self, x, y):
        dtypes = [Level.Tags.Fire, Level.Tags.Physical]
        if self.get_stat('dw'):
            dtypes *= 2
        elif self.get_stat('acid'):
            dtypes.append(Level.Tags.Poison)
        for pt in self.get_impacted_tiles(x, y):
            u = self.caster.level.get_unit_at(pt.x, pt.y)
            if u and Level.are_hostile(u, self.caster) and self.get_stat('acid'):
                b = Level.Buff()
                b.name = "Caustic Magma"
                b.resists[Level.Tags.Poison] = -100
                b.buff_type = Level.BUFF_TYPE_CURSE
                b.asset = ['status', 'amplified_poison']
                b.color = Level.Tags.Nature.color
                u.apply_buff(b, 10)
            for dt in dtypes:
                self.caster.level.deal_damage(pt.x, pt.y, self.get_stat('damage'), dt, self)
            yield

class WHALE(Level.Spell):
    def on_init(self):
        self.name = "Goo Shaver"
        self.max_charges = 4
        self.tags = [Level.Tags.Ice, Level.Tags.Sorcery]
        self.range = 9
        self.level = 6
        self.damage = 17
        self.num_targets = 4
        self.radius = 2
        
        self.upgrades['heavy'] = (1, 4, "Forceful Blocks", "Blocks create floors in their entire radius and deal [physical] damage twice.")

    def get_cones(self, x, y):
        angle = math.pi / 6
        diff_x = self.caster.x - x
        diff_y = self.caster.y - y
        acc = []
        for pt in [Level.Point(x, y), Level.Point(self.caster.x+diff_x, self.caster.y+diff_y)]:
            target = pt
            burst = Level.Burst(self.caster.level, self.caster, self.get_stat('range'), burst_cone_params=Level.BurstConeParams(target, angle), expand_diagonals=True)
            acc.append([p for stage in burst for p in stage if self.caster.level.can_see(self.caster.x, self.caster.y, p.x, p.y)])
        return acc
    
    def get_impacted_tiles(self, x, y):
        cones = self.get_cones(x, y)
        impacted = cones[0] + cones[1]
        return list(set([i for i in impacted if i != Level.Point(self.caster.x, self.caster.y)]))

    def get_description(self):
        return (
            "[{num_targets}:num_targets] ice blocks rain down in a cone in front of the wizard.\n"
            "The same number of ice blocks additionally rain down in a cone behind the wizard.\n"
            "Each ice block deals [{damage}_ice_damage:ice] in a [{radius}-tile_radius:radius], and [{damage}_physical_damage:physical] at the impact point.\n"
            "Ice blocks will create floors on walls and chasms they hit."
        ).format(**self.fmt_dict())
    
    def cast(self, x, y):
        cones = self.get_cones(x, y)
        for c in cones:
            if len(c) < self.get_stat('num_targets'):
                rained = random.choices(c, k=self.get_stat('num_targets'))
            else:
                rained = random.sample(c, self.get_stat('num_targets'))
            for r in rained:
                for _ in range(1+self.get_stat('heavy')):
                    self.caster.level.deal_damage(r.x, r.y, self.get_stat('damage'), Level.Tags.Physical, self)
                if self.caster.level.tiles[r.x][r.y].is_wall() or self.owner.level.tiles[r.x][r.y].is_chasm:
                    self.caster.level.make_floor(r.x, r.y)
                for p in self.caster.level.get_points_in_ball(r.x, r.y, self.get_stat('radius')):
                    self.owner.level.deal_damage(p.x, p.y, self.get_stat('damage'), Level.Tags.Ice, self)
                    if (self.caster.level.tiles[p.x][p.y].is_wall() or self.owner.level.tiles[p.x][p.y].is_chasm) and self.get_stat('heavy'):
                        self.caster.level.make_floor(p.x, p.y)
                for _ in range(3):
                    yield

class Sponge(Level.Spell):
    def on_init(self):
        self.name = "Strike Chain"
        self.max_charges = 5
        self.tags = [Level.Tags.Nature, Level.Tags.Metallic, Level.Tags.Sorcery, Level.Tags.Translocation]
        self.range = 7
        self.level = 4
        self.damage = 13

        self.upgrades['auto'] = (1, 5, "Auto-Potion", "Strike Chain will automatically use healing potions and mana potions it picks up.\nStrike Chain will only use healing potions if your HP is below 50%, and will only use mana potions if you have one-third or less of your total spell charges remaining.")
        self.upgrades['zap'] = (1, 4, "Wire Chain", "Strike Chain will cast your Thunder Strike on units it targets.")
        self.upgrades['range'] = (3, 3)

    def get_description(self):
        return (
            "If targeting an empty tile with a consumable, scroll, ruby heart, or SP orb, pick it up.\n"
            "If targeting a wall with any adjacent empty floors, leap to the closest adjacent empty floor to that wall.\n"
            "If targeting a unit, deal [{damage}_physical_damage:damage]."
        ).format(**self.fmt_dict())

    def can_cast(self, x, y):
        if self.caster.level.tiles[x][y].is_wall() and  Level.distance(self.caster, Level.Point(x, y)) <= self.get_stat('range'):
            return any(self.caster.level.tiles[i.x][i.y].is_floor() for i in self.caster.level.get_adjacent_points(Level.Point(x, y), True, True)) and self.caster.level.can_see(self.caster.x, self.caster.y, x, y, True)
        return Level.Spell.can_cast(self, x, y)
    
    def cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if u:
            u.deal_damage(self.get_stat('damage'), Level.Tags.Physical, self)
            if self.get_stat('zap'):
                ts = Spells.ThunderStrike()
                ts.caster = self.caster
                ts.owner = self.caster
                self.owner.level.act_cast(self.owner, ts, u.x, u.y, pay_costs=False)
        elif self.caster.level.tiles[x][y].is_wall():
            adj = list(self.caster.level.get_adjacent_points(Level.Point(x, y), True, True))
            adj.sort(key=lambda x: Level.distance(self.caster, x))
            pot = adj[0]
            path = self.caster.level.get_points_in_line(Level.Point(self.caster.x, self.caster.y), Level.Point(pot.x, pot.y), find_clear=True)
            for point in path:
                self.caster.level.leap_effect(point.x, point.y, random.choice([t.color for t in self.tags]), self.caster)
                yield
            self.caster.level.act_move(self.caster, pot.x, pot.y, teleport=True)
        elif self.caster.level.tiles[x][y].prop != None:
            p = self.caster.level.tiles[x][y].prop
            if Level.Shop not in type(self.caster.level.tiles[x][y].prop).__bases__:
                p.on_player_enter(self.caster)
                if self.get_stat('auto') and isinstance(p, Level.ItemPickup):
                    charge_ratio = sum(s.cur_charges for s in self.caster.spells)/sum(s.max_charges for s in self.caster.spells)
                    hp_ratio = self.caster.cur_hp/self.caster.max_hp
                    if (p.name == "Mana Potion" and charge_ratio < .33) or (p.name == "Healing Potion" and hp_ratio < .5):
                        p.item.spell.caster = p.item.spell.owner = self.caster
                        self.caster.level.act_cast(self.caster, p.item.spell, self.caster.x, self.caster.y)
                yield

#end mmx

class Pachy(Level.Spell):
    def on_init(self):
        self.name = "Call Elephant"
        self.max_charges = 4
        self.range = 6
        self.tags = [Level.Tags.Conjuration, Level.Tags.Nature]
        self.level = 2

        ex = Monsters.Elephant()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage
        self.minion_range = 6 # for mammoth leaping

        self.must_target_walkable = True
        self.must_target_empty = True

        self.elephant = lambda: self.sourceify(Monsters.Elephant())
        self.elepurple = lambda: self.sourceify(Monsters.CorruptElephant())

        self.upgrades['purp'] = (1, 6, "Purple Pachyderm", "Summon a purple pachyderm instead.")
        self.upgrades['ice'] = (1, 5, "Mammoth", "Summon a mammoth instead.")
    
    def get_extra_examine_tooltips(self):
        return [self.elephant(),
                self.spell_upgrades[0],
                self.elepurple(),
                self.spell_upgrades[1],
                self.mammoth()
                ]

    def get_description(self):
        return (
            "Summon a pachyderm."
        ).format(**self.fmt_dict())
    
    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def mammoth(self):
        m = Level.Unit()
        m.name = "Mammoth"
        m.asset = ["FirstMod", "mammoth"]
        m.resists[Level.Tags.Physical] = 75
        m.resists[Level.Tags.Ice] = 100
        m.resists[Level.Tags.Fire] = 50
        melee = (CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage'), trample=True))
        self.max_hp = self.get_stat('minion_health')
        chg = (CommonContent.LeapAttack(self.get_stat('minion_damage'), self.get_stat('minion_range'), damage_type=Level.Tags.Ice, is_leap=False, charge_bonus=2))
        chg.name = "Chilling Charge"
        rg = CommonContent.RegenBuff(3)
        rg.buff_type = Level.BUFF_TYPE_PASSIVE
        m.buffs = [rg]
        m.spells = [melee, chg]
        m.max_hp = (self.get_stat('minion_health')+8)*2
        m.tags = [Level.Tags.Living, Level.Tags.Ice]
        return m
    
    def cast_instant(self, x, y):
        if self.get_stat('purp'):
            m = self.elepurple()
        elif self.get_stat('ice'):
            m = self.mammoth()
        else:
            m = self.elephant()
        self.summon(m, Level.Point(x, y))

class VenomTax(Level.Buff):

    def on_init(self):
        self.name = "Venom Tax"
        self.color = Level.Tags.Poison.color
        self.description = "Whenever any unit takes damage from this unit's damage aura, heals for that amount plus one."
        self.global_triggers[Level.EventOnDamaged] = self.on_damaged

    def on_damaged(self, evt):
        if Level.are_hostile(self.owner, evt.unit) and evt.source.owner == self.owner and evt.source.name == "Venom Aura":
            self.owner.deal_damage(-(evt.damage+1), Level.Tags.Heal, self)


class VenomSentinel(Level.Spell):
    def on_init(self):
        self.name = "Poison Elemental"
        self.max_charges = 2
        self.range = 6
        self.tags = [Level.Tags.Conjuration, Level.Tags.Nature]
        self.level = 4
        self.minion_health = 80
        self.radius = 5
        self.must_target_empty = True

        self.upgrades['flight'] = (1, 3, "Levistone", "The poison elemental can fly and be summoned on chasms.")
        self.upgrades['venom'] = (1, 5, "Venom Tax", "Whenever a poison elemental's aura deals damage, it heals itself for that amount plus one.")
        self.upgrades['acid'] = (1, 5, "Caustic Field", "The poison elemental's aura deals an extra 1 [fire] damage to units in its radius. The extra hit is treated as coming from this spell.")
    
    def get_extra_examine_tooltips(self):
        return [self.stone()] + self.spell_upgrades

    def can_cast(self, x, y):
        return self.caster.level.can_stand(x, y, self.stone()) and Level.Spell.can_cast(self, x, y)

    def get_description(self):
        return (
            "Summon a poison elemental."
        ).format(**self.fmt_dict())
    
    def stone(self):
        st = Level.Unit()
        st.asset_name = "toxic_stone"
        st.name = "Poison Elemental"
        st.stationary = True
        st.flying = self.get_stat('flight')
        st.tags = [Level.Tags.Poison, Level.Tags.Elemental]
        st.resists[Level.Tags.Physical] = 50
        st.resists[Level.Tags.Arcane] = 50
        st.resists[Level.Tags.Lightning] = 50
        aura = CommonContent.DamageAuraBuff(2, Level.Tags.Poison, self.get_stat('radius'))
        if self.get_stat('acid'):
            aura.on_hit = lambda t: t.deal_damage(1, Level.Tags.Fire, self)
        aura.name = "Venom Aura"
        st.buffs.append(aura)
        st.max_hp = self.get_stat('minion_health')
        if self.get_stat('venom'):
            st.buffs.append(VenomTax())
        return st

    def cast_instant(self, x, y):
        self.summon(self.stone(), Level.Point(x, y))

class IceConvert(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.name == "Conversion"
        self.color = Level.Tags.Fire.color
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.owner_triggers[Level.EventOnDamaged] = self.formchange
    
    def get_tooltip(self):
        return "Changes form when hit by [ice] damage."
    
    def formchange(self, evt):
        if evt.damage_type == Level.Tags.Ice:
            self.owner.Anim = None
            self.owner.asset_name = "dual_demon_ice"
            ind = [s.name for s in self.owner.spells].index("Flame Wisp")
            icebeam = CommonContent.SimpleRangedAttack(name="Frostbeam", damage=self.spell.get_stat('minion_damage'), damage_type=Level.Tags.Ice, range=self.spell.get_stat('minion_range'), beam=True, cool_down=3)
            icebeam.owner = icebeam.caster = self.owner
            self.owner.tags.remove(Level.Tags.Fire)
            self.owner.tags.append(Level.Tags.Ice)
            self.owner.spells[ind] = icebeam
            self.owner.resists[Level.Tags.Fire] -= 150
            self.owner.resists[Level.Tags.Ice] += 150
            self.owner.apply_buff(FireConvert(self.spell))
            if self.spell.get_stat('mage'):
                self.owner.spells = self.owner.spells[1:]
                self.owner.spells.insert(0, self.spell.create_spell(Spells.Iceball, self.owner, 7))
            self.owner.remove_buff(self)

class FireConvert(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.name == "Conversion"
        self.color = Level.Tags.Ice.color
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.owner_triggers[Level.EventOnDamaged] = self.formchange
    
    def get_tooltip(self):
        return "Changes form when hit by [fire] damage."
    
    def formchange(self, evt):
        if evt.damage_type == Level.Tags.Fire:
            self.owner.Anim = None
            self.owner.asset_name = "dual_demon_fire"
            ind = [s.name for s in self.owner.spells].index("Frostbeam")
            icebeam = CommonContent.SimpleRangedAttack(name="Flame Wisp", damage=self.spell.get_stat('minion_damage'), damage_type=Level.Tags.Fire, range=self.spell.get_stat('minion_range')+2, radius=3, cool_down=4)
            icebeam.owner = icebeam.caster = self.owner
            self.owner.tags.remove(Level.Tags.Ice)
            self.owner.tags.append(Level.Tags.Fire)
            self.owner.spells[ind] = icebeam
            self.owner.resists[Level.Tags.Ice] -= 150
            self.owner.resists[Level.Tags.Fire] += 150
            self.owner.apply_buff(IceConvert(self.spell))
            if self.spell.get_stat('mage'):
                self.owner.spells = self.owner.spells[1:]
                self.owner.spells.insert(0, self.spell.create_spell(Spells.MeltSpell, self.owner, 6))
            self.owner.remove_buff(self)

class Formchanger(Level.Spell):
    def on_init(self):
        self.name = "Dual Demon"
        self.max_charges = 2
        self.range = 6
        self.tags = [Level.Tags.Conjuration, Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Dark]
        self.level = 6
        self.minion_health = 66
        self.minion_damage = 9
        self.minion_range = 7
        self.must_target_walkable = True
        self.must_target_empty = True

        self.upgrades['mage'] = (1, 5, "Demon Mage", "The dual demon can cast your Melt in its fire form, and your Iceball in its ice form.\nThese have a 6 and 7 turn cooldown, respectively.")

    def create_spell(self, s, u, c):
        obj = s()
        obj.caster = obj.owner = u
        obj.statholder = self.caster
        obj.cool_down = c
        return obj

    def get_description(self):
        return (
            "Summon the dual demon near yourself, starting in its fire form."
        ).format(**self.fmt_dict())
    
    def create_demon(self):
        d = Level.Unit()
        d.max_hp = self.get_stat('minion_health')
        d.resists[Level.Tags.Lightning] = 50
        d.resists[Level.Tags.Fire] = 100
        d.resists[Level.Tags.Ice] = -50
        d.asset_name = "dual_demon_fire"
        d.buffs.append(IceConvert(self))
        d.name = "Dual Demon"
        d.tags = [Level.Tags.Fire, Level.Tags.Demon]
        fball = CommonContent.SimpleRangedAttack(name="Flame Wisp", damage=self.get_stat('minion_damage'), damage_type=Level.Tags.Fire, range=self.get_stat('minion_range'), radius=3, cool_down=4)
        whap = CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage')+7)
        d.spells = [fball, whap]
        if self.get_stat('mage'):
            d.spells.insert(0, self.create_spell(Spells.MeltSpell, d, 6))
        return d
    
    def cast_instant(self, x, y):
        self.summon(self.create_demon(), Level.Point(x, y))

class ChaosPlants(Level.Spell):
    def on_init(self):
        self.name = "Chaos Arbor"
        self.max_charges = 1
        self.range = 3
        self.tags = [Level.Tags.Conjuration, Level.Tags.Chaos, Level.Tags.Nature]
        self.level = 6
        self.entities = []
        self.turns = 0

        ex = BossSpawns.apply_modifier(BossSpawns.Chaostouched, Monsters.Spriggan())
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[1].damage
        self.minion_range = ex.spells[0].range

        self.upgrades['ent'] = (1, 5, "Great Trees", "Each spriggan has a 10% chance to instead be a treant.")
        self.upgrades['minion_range'] = (3, 4, "Chaotic Foresight")
        self.upgrades['ghost'] = (1, 5, "Ghosts of Madness", "Each spriggan has a 20% chance to also spawn with the ghostly modifier.")

    def get_description(self):
        return (
            "Each turn you channel this spell, summon a chaos spriggan.\n"
            "All units summoned by this spell will instantly die when channeling stops.\n"
            "Spriggan bushes spawned by spriggans from this spell and spriggans maturing from those bushes will not die, but do not gain any bonuses from this spell."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [
                self.create_spriggy('c'),
                self.spell_upgrades[0],
                self.create_spriggy('c', True),
                self.spell_upgrades[1],
                self.spell_upgrades[2],
                self.create_spriggy('ch')
                ]
    
    def create_spriggy(self, type, is_treant=False):
        base = Monsters.Spriggan() if not is_treant else Monsters.Treant()
        if type == 'c':
            m = BossSpawns.apply_modifier(BossSpawns.Chaostouched, base)
        elif type == 'ch':
            m  = BossSpawns.apply_modifier(BossSpawns.Ghostly, BossSpawns.apply_modifier(BossSpawns.Chaostouched, base))
        CommonContent.apply_minion_bonuses(self, m)
        return m

    def cast(self, x, y, channel_cast=False):
        if not channel_cast:
            self.turns = 0
            chn = Level.ChannelBuff(self.cast, Level.Point(x, y))
            chn.on_unapplied = lambda: [u.kill() for u in self.entities if hasattr(u, 'level')] + [self.entities.clear()] # the king of jank, kills and clears in one fell swoop
            self.caster.apply_buff(chn)
            return
        else:
            sprigtype = 'c'
            if self.get_stat('ghost') and random.random() < .2:
                sprigtype = 'ch'
            mon = self.create_spriggy(sprigtype, (self.get_stat('ent') and random.random() < .1))
            self.turns += 1
            self.entities.append(mon)
            self.summon(mon, Level.Point(x, y))
            yield

class OrbPonderanceBuff(Level.Buff):

    def __init__(self, spell, dur):
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.advfunction = None
        self.spell = spell
        self.dur = dur
        self.color = Level.Tags.Orb.color
    
    def on_applied(self, owner):
        o = self.owner.get_buff(Spells.OrbBuff)
        self.advfunction = o.on_advance
        o.on_advance = lambda: o.spell.on_orb_move(self.owner, self.owner)
        if self.owner.turns_to_death is not None:
            self.owner.turns_to_death += self.dur
    
    def on_attempt_advance(self):
        if self.spell.get_stat('protect'):
            self.owner.add_shields(1)
        return False
    
    def on_unapplied(self):
        o = self.owner.get_buff(Spells.OrbBuff)
        if self.spell.get_stat('blast'):
            for _ in range(self.dur//2):
                o.on_advance()
        o.on_advance = self.advfunction 

    def get_tooltip(self):
        return "Orb is being pondered!"

class PonderTheOrb(Level.Spell):
    def on_init(self):
        self.name = "Orb Focus"
        self.max_charges = 2
        self.range = 50
        self.tags = [Level.Tags.Enchantment, Level.Tags.Orb]
        self.level = 5
        self.requires_los = False
        self.can_target_empty = False
        self.duration = 4

        self.upgrades['protect'] = (1, 4, "Focus Shield", "Pondered orbs gain 1 shield per turn.")
        self.upgrades['blast'] = (1, 5, "Unleashed Concentration", "When the orb becomes mobile again, it activates its movement effect a number of times equal to half this spell's duration before moving.")
        self.upgrades['multi'] = (1, 3, "Multitasking", "The Wizard is no longer [stunned] when casting this spell.")

    def can_cast(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        return u and not Level.are_hostile(self.caster, u) and u.has_buff(Spells.OrbBuff)

    def get_description(self):
        return (
            "Target [orb] minion cannot move for [{duration}_turns:duration], but gains the same amount of minion duration.\n"
            "Its per-turn effects will still activate as normal for the duration.\n"
            "The Wizard is [stunned] for half that duration."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u or not u.has_buff(Spells.OrbBuff):
            return
        dur = self.get_stat('duration')
        u.apply_buff(OrbPonderanceBuff(self, dur), dur)
        if not self.get_stat('multi'):
            self.caster.apply_buff(Level.Stun(), dur//2)

class WormBurrowBuff(Level.Buff):

    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.spell = spell
        self.color = Level.Tags.Physical.color
        self.name = "Worm Burrow"

    def on_advance(self):
        pts = [p for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.spell.get_stat('radius'))]
        filtered = [p for p in pts if self.owner.level.tiles[p.x][p.y].is_wall() or (self.owner.level.tiles[p.x][p.y].is_chasm and self.spell.get_stat('chasm'))]
        if not filtered:
            return
        targets = filtered if len(filtered) <= self.spell.get_stat('num_targets') else random.sample(filtered, self.spell.get_stat('num_targets'))
        for t in targets:
            self.owner.level.make_floor(t.x, t.y)
            w = self.spell.rwurm() if not self.spell.get_stat('were') else self.spell.wwurm()
            if self.spell.get_stat('incubate'):
                w.buffs.append(CommonContent.MatureInto(self.spell.sfish, 23))
            self.spell.summon(w, t)

            
class WormBurrow(Level.Spell):
    def on_init(self):
        self.name = "Worm Burrows"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Conjuration, Level.Tags.Nature]
        self.level = 4
        self.duration = 4
        self.num_targets = 2
        self.radius = 6

        ex = Monsters.RockWurm()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        self.rwurm = lambda: self.sourceify(Monsters.RockWurm())
        self.wwurm = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Lycanthrope, Monsters.RockWurm()))
        self.sfish = lambda: self.sourceify(Monsters.StoneFish())

        self.upgrades['chasm'] = (1, 4, "Depth Adaptations", "Worms can be summoned from chasms in addition to wall tiles.\nAffected chasms will become floors.")
        self.upgrades['were'] = (1, 6, "Full Moon Burrow", "Summon wereworms instead of normal ones.")
        self.upgrades['incubate'] = (1, 5, "Worm Incubation", "Summoned worms will become stonefish in 23 turns.")

    def get_extra_examine_tooltips(self):
        return [
                self.rwurm(),
                self.spell_upgrades[0],
                self.spell_upgrades[1],
                self.wwurm(),
                self.spell_upgrades[2],
                self.sfish()
                ]

    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        if m.name == "Wererock Worm":
            m.max_hp = self.get_stat('minion_health')
        return m

    def get_description(self):
        return (
            "Each turn, destroy [{num_targets}:num_targets] random walls in a [{radius}-tile_radius:radius] and summon rockworms at those locations.\n"
            "This effect lasts [{duration}_turns:duration]"
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.caster.apply_buff(WormBurrowBuff(self), self.get_stat('duration'))

class PoisonBreath(Monsters.BreathWeapon):

    def __init__(self, spell):
        Monsters.BreathWeapon.__init__(self)
        self.name = "Poison Breath"
        self.damage_type = Level.Tags.Poison
        self.damage = spell.get_stat("breath_damage")
        self.range = spell.get_stat("minion_range")
        self.duration = spell.get_stat("duration")
        self.spell = spell
    
    def get_description(self):
        return "Inflicts poison for %i turns and deals damage in a cone." % self.get_stat("duration")

    def per_square_effect(self, x, y):
        unit = self.caster.level.get_unit_at(x, y)
        if not unit:
            self.caster.level.show_effect(x, y, Level.Tags.Poison)
        else:
            if not Level.are_hostile(unit, self.caster) and self.spell.get_stat('shape'):
                thorn = CommonContent.Thorns(5, Level.Tags.Poison)
                thorn.name = "Poison Shape"
                thorn.resists[Level.Tags.Poison] = 100
                unit.apply_buff(thorn, self.get_stat('duration'))
            elif (psn := unit.get_buff(CommonContent.Poison)) and self.spell.get_stat('stack'):
                psn.turns_left += self.get_stat('duration')
            else:
                unit.apply_buff(CommonContent.Poison(), self.get_stat("duration"))
            unit.deal_damage(self.get_stat("damage"), Level.Tags.Poison, self)

class PoisonDragon(Level.Spell):
    def on_init(self):
        self.name = "Venom Drake"
        self.max_charges = 2
        self.tags = [Level.Tags.Nature, Level.Tags.Conjuration, Level.Tags.Dragon]
        self.level = 4
        self.minion_health = 45
        self.minion_range = 7
        self.breath_damage = 9
        self.minion_damage = 8
        self.duration = 15

        self.upgrades['stack'] = (1, 4, "Venom Drench", "Any poison inflicted by the drake will add to the target's poison duration if it is already poisoned.")
        self.upgrades['shape'] = (1, 5, "Shape Poison", "Allies caught in the drake's breath gain melee retaliation dealing [poison] damage and [poison] immunity for the same durationinstead of being damaged or poisoned.")

    def get_extra_examine_tooltips(self):
        return [self.drake()] + self.spell_upgrades
    
    def drake(self):
        d = Level.Unit()
        d.max_hp = self.get_stat('minion_health')
        d.spells = [PoisonBreath(self), CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage'))]
        d.name = "Venom Drake"
        d.asset = ["FirstMod", "poison_drake"]
        d.tags = [Level.Tags.Living, Level.Tags.Poison]
        d.resists[Level.Tags.Poison] = 100
        return d

    def get_description(self):
        return (
            "Summon a venom drake at target tile."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.summon(self.drake(), Level.Point(x, y))

class SaltJudgment(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.name = "Punishment of Salt"
        self.color = Level.Tags.Construct.color
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.global_triggers[Level.EventOnMoved] = self.proc_damage
        self.global_triggers[Level.EventOnUnitAdded] = self.process_unit
        self.dist_table = {}
    
    def get_tooltip(self):
        return "Deals %d [holy] and [poison] damage to enemies that move closer to it." % self.spell.get_stat('minion_damage')
    
    def process_unit(self, evt):
        if evt.unit != self.owner:
            self.add_table_entry(evt.unit)
    
    def add_table_entry(self, u):
        self.dist_table[u] = Level.distance(self.owner, u)
    
    def proc_damage(self, evt):
        if evt.unit not in self.dist_table.keys() or not Level.are_hostile(evt.unit, self.owner):
            return
        if Level.distance(self.owner, Level.Point(evt.x, evt.y)) < self.dist_table[evt.unit]:
            for d in [Level.Tags.Holy, Level.Tags.Poison]:
                evt.unit.deal_damage(self.spell.get_stat('minion_damage'), d, self)

class CurseOfSalt(Level.Upgrade):

    def on_init(self):
        self.name = "Salt Curse"
        self.description = "Any incapacitated enemy unit in line of sight loses 100 [holy] resist."
        self.color = Level.Tags.Poison.color
        self.global_triggers[Level.EventOnBuffApply] = self.on_buff_apply
    
    def on_buff_apply(self, evt):
        if not Level.are_hostile(evt.unit, self.owner):
            return
        if Level.Stun not in type(evt.buff).__bases__ and type(evt.buff) != Level.Stun:
            return
        if evt.unit not in self.owner.level.get_units_in_los(self.owner):
            return
        self.change_buff(evt.buff)

    def on_applied(self, owner):
        for unit in self.owner.level.get_units_in_los(self.owner):
            if not Level.are_hostile(unit, self.owner):
                continue
            for buff in unit.buffs:
                if Level.Stun not in type(buff).__bases__ and type(buff) != Level.Stun:
                    continue
                self.change_buff(buff)

    def change_buff(self, buff):
        buff.owner.resists[Level.Tags.Holy] -= 100
        buff.resists[Level.Tags.Holy] = -100
    
class SaltEffigy(Level.Spell):
    def on_init(self):
        self.name = "Pillar of Salt"
        self.max_charges = 2
        self.tags = [Level.Tags.Nature, Level.Tags.Conjuration, Level.Tags.Holy]
        self.level = 7
        self.minion_health = 119
        self.minion_damage = 4

        self.upgrades['curse'] = (1, 5, "Salt Curse", "Any incapacitated enemy unit in line of sight of the pillar loses 100 [holy] resist.")
        self.upgrades['rain'] = (1, 6, "Rain of Fire", "The pillar can cast Pillar of Fire on a 20 turn cooldown.\nThis Pillar of fire does NOT gain your upgrades and bonuses.")
        self.upgrades['wrath'] = (1, 7, "Blinding Wrath", "The pillar can cast Blinding Light on a 16 turn cooldown.\nThis Blinding Light does NOT gain your upgrades and bonuses.")

    def get_extra_examine_tooltips(self):
        return [self.drake()] + self.spell_upgrades
    
    def drake(self):
        d = Level.Unit()
        d.max_hp = self.get_stat('minion_health')
        d.name = "Salt Pillar"
        d.asset = ["FirstMod", "salt_elemental"]
        d.tags = [Level.Tags.Poison, Level.Tags.Holy, Level.Tags.Construct]
        d.resists[Level.Tags.Poison] = 100
        d.resists[Level.Tags.Holy] = 100
        d.resists[Level.Tags.Physical] = 25
        d.stationary = True
        if self.get_stat('rain'):
            db = Spells.FlameStrikeSpell()
            db.caster = d
            db.statholder = d
            db.owner = d
            db.cool_down = 20
            d.spells.insert(0, db)
        if self.get_stat('wrath'):
            db = Spells.BlindingLightSpell()
            db.caster = d
            db.statholder = d
            db.owner = d
            db.cool_down = 16
            d.spells.insert(0, db)
        d.buffs.append(SaltJudgment(self))
        if self.get_stat('curse'):
            d.buffs.append(CurseOfSalt())
        return d

    def get_description(self):
        return (
            "Summon a pillar of salt on target tile."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        pillar = self.drake()
        self.summon(pillar, Level.Point(x, y))
        pillar.buffs[0].dist_table = {u:Level.distance(pillar, u) for u in self.caster.level.units}

class ChaosBurn(Level.Spell):
    def on_init(self):
        self.name = "Chaotic Flame"
        self.max_charges = 5
        self.range = 7
        self.num_targets = 16
        self.tags = [Level.Tags.Fire, Level.Tags.Chaos, Level.Tags.Sorcery]
        self.level = 4
        self.can_target_empty = False

        self.upgrades['perfect'] = (1, 5, "Perfect Chaos", "The target also takes the same number of hits of [ice] damage.")
        self.upgrades['num_targets'] = (8, 4, "Enhanced Blast")
        self.upgrades['requires_los'] = (-1, 4, "Blindcasting", "Chaotic Flame can be cast without line of sight.")

    def get_description(self):
        return (
            "Deal a fixed 1 [fire] damage, then 1 fixed [lightning] or [physical] damage [{num_targets}:num_targets] times to target unit."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.owner.level.get_unit_at(x, y)
        if not u:
            return
        for _ in range(self.get_stat('num_targets')):
            u.deal_damage(1, Level.Tags.Fire, self)
            u.deal_damage(1, random.choice([Level.Tags.Lightning, Level.Tags.Physical]), self)
            if self.get_stat('perfect'):
                u.deal_damage(1, Level.Tags.Ice, self)

class MeltCreeperBuff(Level.Buff):

    def __init__(self, spell, origin):
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.stack_type = Level.STACK_INTENSITY # to allow multiple melt creepers
        self.spell = spell
        self.color = Level.Tags.Fire.color
        self.name = "Melt Creep"
        self.burning = set([origin])

    def on_advance(self):
        for b in self.burning:
            u = self.owner.level.get_unit_at(b.x, b.y)
            if u and Level.are_hostile(u, self.owner) and self.spell.get_stat('purge'):
                for b in u.buffs:
                    if b.buff_type == Level.BUFF_TYPE_BLESS:
                        u.remove_buff(b)
            self.owner.level.deal_damage(b.x, b.y, self.spell.get_stat('damage'), Level.Tags.Fire, self.spell)
        doublespread = len(self.burning) < 40 and self.spell.get_stat('double')
        for _ in range(1+doublespread):
            for v in self.burning.copy():
                for s in [p for p in self.owner.level.get_adjacent_points(v, filter_walkable=False) if p not in self.burning]:
                    if random.random() < .04:
                        self.burning.add(s)
                        if self.owner.level.tiles[s.x][s.y].is_wall():
                            self.owner.level.make_floor(s.x, s.y)
                    

class MeltCreep(Level.Spell):
    def on_init(self):
        self.name = "Melt Creeper"
        self.max_charges = 3
        self.range = 7
        self.requires_los = False
        self.tags = [Level.Tags.Fire, Level.Tags.Enchantment]
        self.level = 5
        self.damage = 6
        self.duration = 50

        self.upgrades['double'] = (1, 6, "Double Creeper", "If a flame has spread to less than 40 tiles, it attempts to spread twice instead of once.")
        self.upgrades['purge'] = (1, 5, "Purging Flame", "This spell removes all positive effects from enemies prior to dealing damage.")

    def get_description(self):
        return (
            "Leave behind a small flame on target tile.\n"
            "Each turn, the flame has a 4% chance to spread to any adjacent tile, destroying walls it spreads to.\n"
            "The flame deals [{damage}_fire_damage:fire] to units standing in it each turn.\n"
            "The flame lasts [{duration}_turns:duration]."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.caster.apply_buff(MeltCreeperBuff(self, Level.Point(x, y)), self.get_stat('duration'))

class Shamblize(Level.Buff):

    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.spell = spell
        self.description = "Takes %d dark damage per turn and respawns as a bone shambler with the same HP on death." % self.spell.get_stat('damage')
        self.color = Level.Tags.Dark.color
        self.name = "Preserved Bones"
        self.owner_triggers[Level.EventOnDeath] = self.on_death

    def on_advance(self):
        self.owner.deal_damage(self.spell.get_stat('damage'), Level.Tags.Dark, self.spell)

    def on_death(self, evt):
        self.owner.level.queue_spell(self.spawn())

    def child(self, hp, parent):
        u = Monsters.BoneShambler(hp)
        if self.spell.get_stat('storm'):
            u = BossSpawns.apply_modifier(BossSpawns.Stormtouched, Monsters.BoneShambler(hp))
        u.max_hp = hp
        if u.has_buff(Monsters.SplittingBuff):
            u.get_buff(Monsters.SplittingBuff).spawner = self.child(u.max_hp//2, u)
        if Level.Tags.Living in parent.tags and self.spell.get_stat('flesh'):
            u.tags.append(Level.Tags.Living)
        elif self.spell.get_stat('holy'):
            u.resists[Level.Tags.Holy] = 50
            if u.max_hp >= 16:
                u.tags.append(Level.Tags.Holy)
        return u

    def spawn(self):
        u = Monsters.BoneShambler(self.owner.max_hp)
        if self.spell.get_stat('storm'):
            u = BossSpawns.apply_modifier(BossSpawns.Stormtouched, Monsters.BoneShambler(self.owner.max_hp))
        CommonContent.apply_minion_bonuses(self.spell, u)
        if u.has_buff(Monsters.SplittingBuff):
            u.get_buff(Monsters.SplittingBuff).spawner = self.child(u.max_hp//2, self.owner)
        u.max_hp = self.owner.max_hp
        if Level.Tags.Living in self.owner.tags and self.spell.get_stat('flesh'):
            u.tags.append(Level.Tags.Living)
        elif self.spell.get_stat('holy'):
            u.resists[Level.Tags.Holy] = 50
            if u.max_hp >= 16:
                u.tags.append(Level.Tags.Holy)
        self.summon(u)
        yield

class Boney(Level.Spell):
    def on_init(self):
        self.name = "Bone Preserve"
        self.max_charges = 2
        self.range = 6
        self.requires_los = False
        self.tags = [Level.Tags.Dark, Level.Tags.Enchantment]
        self.level = 4
        self.damage = 18

        self.upgrades['storm'] = (1, 7, "Stormbone Shambling", "Summon electric bone shamblers instead of normal ones.")
        self.upgrades['flesh'] = (1, 6, "Flesh Guise", "Shamblers become [living] if the target was [living] when it died.")
        self.upgrades['holy'] = (1, 7, "Saint's Corpse", "Shamblers have their [holy] resist set to 50, and bone shamblers with 16 or more HP gain [holy].")


    def get_description(self):
        return (
            "Target ally takes [{damage}_dark_damage:dark] per turn until it dies, after which it becomes a bone shambler with the same HP."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u or Level.are_hostile(u, self.owner):
            return
        u.apply_buff(Shamblize(self))

class BizarroKnightBuff(Level.Buff):

    def __init__(self, summoner, spell, ktype):
        Level.Buff.__init__(self)
        self.summoner = summoner
        self.spell = spell
        self.ktype = ktype

    def on_init(self):
        self.name = "Bizarre Bound Knight"
        self.color = Level.Tags.Dark.color
        self.owner_triggers[Level.EventOnDeath] = self.on_death
                
    def get_tooltip(self):
        base = "On death, poisons its summoner for 30 turns"
        if self.ktype == "s" and self.spell.get_stat('burn'):
            base += ", acidifies its summoner for 30 turns, and reduces its [fire] resist by 50 for 10 turns"
        elif self.ktype == "f" and self.spell.get_stat('fae'):
            base += ", acidifies its summoner for 30 turns, and reduces its [arcane] resist by 100 for 10 turns"
        elif self.ktype == "i" and self.spell.get_stat('ice'):
            base += " and [freezes:ice] them for 3 turns"
        return base

    def on_death(self, evt):
        if (self.ktype == "s" and self.spell.get_stat('burn')) or (self.ktype == "f" and self.spell.get_stat('fae')):
            self.summoner.apply_buff(CommonContent.Acidified(), 30)
            res = Level.Buff()
            res.name = "Punishment"
            res.stack_type = Level.STACK_INTENSITY
            if (self.ktype == "s" and self.spell.get_stat('burn')):
                res.resists[Level.Tags.Fire] = -50
                res.color = Level.Tags.Fire.color
                self.summoner.apply_buff(res, 10)
            if (self.ktype == "f" and self.spell.get_stat('fae')):
                res.resists[Level.Tags.Arcane] = -100
                res.color = Level.Tags.Arcane.color
                self.summoner.apply_buff(res, 10)
        if (self.ktype == "i" and self.spell.get_stat('ice')):
            self.summoner.apply_buff(CommonContent.FrozenBuff(), 3)
        if (psn := self.summoner.get_buff(CommonContent.Poison)):
            psn.turns_left += 30
        else:
            self.summoner.apply_buff(CommonContent.Poison(), 30)

class BizarreOath(Level.Spell):
    def on_init(self):
        self.name = "Bizarro Court"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Conjuration, Level.Tags.Dark]
        self.level = 5

        ex = BossSpawns.apply_modifier(BossSpawns.Flametouched, Monsters.BoneKnight())
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        self.upgrades['twi'] = (1, 4, "Bizarre Archery", "Additionally summon an immortal bone archer.")
        self.upgrades['burn'] = (1, 6, "Strangeness of Fire", "The burning bone knight gains 1 aura radius and can cast your Melt spell on a 7 turn cooldown.\nThe wizard is acidified for 30 turns and loses 50 fire resist for 10 turns when it dies.")
        self.upgrades['ice'] = (1, 6, "Peculiarity of Ice", "The icy bone knight gains 100 extra max HP and its iceball is replaced with your Iceball spell on a 7 turn cooldown. Its death and reduces [ice] resist. \nThe wizard is acidified for 30 turns and frozen for 3 turns when it dies.")
        self.upgrades['fae'] = (1, 6, "Fae Oddities", "The fae bone knight's shield regeneration activates in 3 turns instead of 5 and can grant a maximum of 5 SH. It additionally gains your Devour Mind spell on a 3 turn cooldown.\nThe wizard is acidified for 30 turns and loses 100 arcane resist for 10 turns when it dies.")


    def get_description(self):
        return (
            "Summon a burning bone knight, fae bone knight, and icy bone knight near yourself.\n"
            "Whenever a knight dies, the wizard is poisoned for 30 turns, adding to any existing poison duration."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.bone("s"),
                self.bone("f"),
                self.bone("i"),
                self.spell_upgrades[0],
                self.archer()
                ] + self.spell_upgrades[1:]
    
    def archer(self):
        k = BossSpawns.apply_modifier(BossSpawns.Immortal, Variants.BoneKnightArcher())
        CommonContent.apply_minion_bonuses(self, k)
        k.buffs.append(BizarroKnightBuff(self.owner, self, "im"))
        return k
    
    def bone(self, element):
        mod = BossSpawns.Flametouched if element == "s" else (BossSpawns.Faetouched if element == "f" else BossSpawns.Icy)
        k = BossSpawns.apply_modifier(mod, Monsters.BoneKnight())
        CommonContent.apply_minion_bonuses(self, k)
        k.buffs.append(BizarroKnightBuff(self.owner, self, element))
        if self.get_stat('burn') and element == "s":
            k.buffs[0].radius += 1
            m = Spells.MeltSpell()
            m.statholder = self.caster
            m.owner = m.caster = k
            m.cool_down = 7
            k.spells.insert(0, m)
        elif self.get_stat('ice') and element == "i":
            k.max_hp += 100
            m = Spells.Iceball()
            m.statholder = self.caster
            m.owner = m.caster = k
            m.cool_down = 7
            k.spells[0] = m
        elif self.get_stat('fae') and element == "f":
            k.buffs[0].shield_freq = 3
            k.buffs[0].shield_max = 5
            m = Spells.MindDevour()
            m.statholder = self.caster
            m.owner = m.caster = k
            m.cool_down = 3
            k.spells.insert(0, m)
        return k
    
    def cast_instant(self, x, y):
        bones = [self.bone("s"), self.bone("i"), self.bone("f")]
        if self.get_stat('twi'):
            bones.append(self.archer())
        for b in bones:
            self.summon(b, self.caster)

class GoldWeb(Level.Cloud):

    def __init__(self):
        Level.Cloud.__init__(self)
        self.name = "Golden Web"
        self.color = Level.Tags.Holy.color
        self.duration = 10
        self.sdur = 2
        self.dmg = 5
        self.is_destructible = True
        self.description = "Any unit hostile to the web's creator is stunned for 2 turns and takes 5 holy damage. This destroys the web.%s" % ("\n\nFire damage destroys webs." if self.is_destructible else "")

        self.asset_name = 'web'

    def on_unit_enter(self, unit):
        if Level.are_hostile(self.owner, unit):
            unit.apply_buff(Level.Stun(), self.sdur)
            unit.deal_damage(self.dmg, Level.Tags.Holy, self)
            self.kill()

    def on_damage(self, dtype):
        if dtype == Level.Tags.Fire and self.is_destructible:
            self.kill()

def gold_spawn_webs(unit):

    adj = unit.level.get_points_in_ball(unit.x, unit.y, 1.5)
    candidates = [p for p in adj if unit.level.get_unit_at(p.x, p.y) is None and unit.level.tiles[p.x][p.y].can_see]

    if candidates:
        p = random.choice(candidates)
        web = GoldWeb()
        web.owner = unit
        unit.level.add_obj(web, p.x, p.y)
                
class GoldSpiderBuff(Level.Buff):

    def on_advance(self):

        # Do not make webs if there are no enemy units
        if not any(Level.are_hostile(u, self.owner) for u in self.owner.level.units):
            return
        gold_spawn_webs(self.owner)

    def get_tooltip(self):
        return "Weaves gold webs each turn"

class GoldSpiderThorns(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        self.dmg = 5 + (self.spell.get_stat('minion_damage')-self.spell.minion_damage)
        Level.Buff.__init__(self)
        self.name = "Gold Thorns"
        self.description = "Deals %d holy damage to enemy attackers" % (self.dmg)
        self.color = Level.Tags.Holy.color

    def on_init(self):
        self.owner_triggers[Level.EventOnDamaged] = self.on_spell

    def on_spell(self, evt):
        victim = evt.source if type(evt.source) == Level.Unit else evt.source.owner
        if not Level.are_hostile(victim, self.owner):
            return
        self.owner.level.queue_spell(self.do_thorns(victim))

    def do_thorns(self, unit):
        unit.deal_damage(self.dmg, Level.Tags.Holy, self)
        yield

class GoldSpider(Spells.OrbSpell):
    def on_init(self):
        self.name = "Golden Orb Spider"
        self.range = 9
        self.max_charges = 1

        self.melt_walls = False

        self.minion_health = 80
        self.minion_damage = 14
        self.radius = 3
        
        self.tags = [Level.Tags.Nature, Level.Tags.Holy, Level.Tags.Orb, Level.Tags.Conjuration]
        self.level = 7

        self.upgrades['urt'] = (1, 7, "Righteous Urtication", "The spider's retaliation in its true form now has no range limit and benefits from bonuses to minion damage.")
        self.upgrades['aur'] = (1, 5, "Aureal Silk", "Gold webs created by the spider's orb form stun twice as long, deal 10 holy damage, and are immune to fire damage.")

    def get_extra_examine_tooltips(self):
        return [self.trueform()] + self.spell_upgrades

    def get_description(self):
        return ("Summon a golden orb spider next to the caster.\n"
                "The spider has [{minion_health}_HP:minion_health] and starts in an orb-like state, floating one tile towards the target each turn.\n"
                "The orb has a 30% chance each turn to weave a gold web in a [{radius}-tile_radius:radius] around itself."
                "These gold webs do not hinder allies, but stun and deal fixed 5 [holy] damage to enemies entering them.\n"
                "The spider's orb form can be destroyed by [poison] damage.\n"
                "When the spider's orb form is destroyed or expires, it respawns in its true form.").format(**self.fmt_dict())
        
    def on_make_orb(self, orb):
        orb.resists[Level.Tags.Poison] = 0
        orb.name = "Golden Orb Spider"
        orb.tags = [Level.Tags.Holy, Level.Tags.Spider]
        orb.buffs.append(CommonContent.SpawnOnDeath(self.trueform, 1))
        orb.recolor_primary = Level.Tags.Holy.color
        orb.recolor_secondary = Level.Tags.Fire.color
        orb.asset = ['FirstMod', 'toxic_orb']
    
    def trueform(self):
        spoder = Level.Unit()
        spoder.max_hp = self.minion_health+20
        spoder.tags = [Level.Tags.Living, Level.Tags.Spider, Level.Tags.Holy, Level.Tags.Nature]
        spoder.spells.append(CommonContent.SimpleMeleeAttack(self.minion_damage, buff=CommonContent.Poison, buff_duration=15))
        spoder.name = "True Golden Orb Spider"
        spoder.asset_name = "dark_spider"
        spoder.recolor_primary = Level.Tags.Holy.color
        spoder.recolor_secondary = Level.Tags.Fire.color
        if self.get_stat('urt'):
            spoder.buffs.append(GoldSpiderThorns(self))
        else:
            spoder.buffs.append(CommonContent.Thorns(5, Level.Tags.Holy))
        spoder.buffs.append(GoldSpiderBuff())
        return spoder
                
    def on_orb_move(self, orb, next_point):
        for t in self.owner.level.get_tiles_in_ball(orb.x, orb.y, self.get_stat('radius')):
            if random.random() < .3:
                w = GoldWeb()
                if self.get_stat('aur'):
                    w.sdur = 4
                    w.is_destructible = False
                    w.dmg = 10
                w.owner = orb
                orb.level.add_obj(w, t.x, t.y)


class GCFW(Level.Spell):
    def on_init(self):
        self.name = "Gem of Eternity"
        self.max_charges = 4
        self.tags = [Level.Tags.Arcane, Level.Tags.Metallic, Level.Tags.Conjuration]
        self.level = 5
        self.radius = 5

        self.minion_health = 120

        self.upgrades['fast'] = (2, 5, "Charged Gem", "The Gem's Wake of Eternity cooldown is reduced by 2.")
        self.upgrades['banishing'] = (1, 4, "Wake of Exile", "The Gem gains an extra 13% additive chance to teleport hit units.")
        self.upgrades['forgotten'] = (1, 5, "Forgotten's Wrath", "If you have a [demon] ally and at least 1 replica, Wake of Eternity hits the target's lowest resistance and deals at least 2 damage.")

    def get_description(self):
        return (
            "Summon the Gem of Eternity.\n"
            "Whenever a new Gem would be summoned, all other Gems become replicas with one-fifth of the Gem's HP.\n"
            "The real Gem gains 1 radius to Wake of Eternity for each living replica at summon time."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.gem()] + self.spell_upgrades
    
    def gem(self):
        gem = Level.Unit()
        gem.asset = ['FirstMod', 'eternity_gem']
        gem.name = "Gem of Eternity"
        gem.max_hp = self.get_stat('minion_health')
        gem.stationary = gem.flying = True
        gem.resists[Level.Tags.Arcane] = 100
        randmod = .2 + .13*self.get_stat('banishing')
        def woe_onhit(c, t):
            if Level.are_hostile(t, c):
                t.shields = 0
                dmg = t.cur_hp//5
                tag = Level.Tags.Arcane
                if any(u.name == "Replica Gem of Eternity" for u in self.caster.level.units) and any(Level.Tags.Demon in u.tags and not Level.are_hostile(u, c) for u in self.caster.level.units) and self.get_stat('forgotten'):
                    dmg = max(2, dmg)
                    minres = {k:v for k,v in t.resists.items() if v == min(t.resists.values())}.keys()
                    tag = random.choice(list(minres))
                t.deal_damage(dmg, tag, [s for s in c.spells if s.name == "Wake of Eternity"][0])
                if random.random() < randmod:
                    valids = [p for p in c.level.iter_tiles() if t.level.can_move(t, p.x, p.y, teleport=True)]
                    if valids:
                        valids.sort(key=lambda p: Level.distance(t, p))
                        p = valids[-1]
                        t.level.act_move(t, p.x, p.y, teleport=True)
        wake = CommonContent.SimpleBurst(0, self.get_stat('radius'), Level.Tags.Arcane, 4-self.get_stat('fast'), True, woe_onhit, "Removes all shields, deals 20%% of target's current HP as [arcane] damage, and has a %d%% chance to teleport hit units as far as possible away from the gem" % int(randmod*100))
        wake.name = "Wake of Eternity"
        gem.spells.append(wake)
        gem.tags = [Level.Tags.Metallic, Level.Tags.Arcane]
        return gem
    
    def cast_instant(self, x, y):
        g = self.gem()
        to_replica = [u for u in self.caster.level.units if u.source == self and not getattr(u, "is_replica_gem", False)]
        for r in to_replica:
            r.max_hp = r.max_hp // 5
            r.cur_hp = r.cur_hp // 5
            r.spells = []
            r.name = "Replica " + r.name
            setattr(r, "is_replica_gem", True)
        replicas = [u for u in self.caster.level.units if u.source == self and getattr(u, "is_replica_gem", False)]
        g.spells[0].radius += len(replicas)
        self.summon(g, Level.Point(x, y))

class SelfSacrifice(Upgrades.Upgrade):
    def on_init(self):
        self.prereq = RitualOfLife
        self.name = "Self-Sacrifice"
        self.level = 5
        self.description = "Double the amount of damage the wizard takes during channeling is evenly distributed to allies in the radius as max HP."
        self.owner_triggers[Level.EventOnDamaged] = self.ondmg

    def ondmg(self, evt):
        instance = [s for s in self.owner.spells if type(s) == RitualOfLife][0]
        if instance:
            instance.sacrifice_damage += evt.damage*2


class RitualOfLife(Level.Spell):

    def on_init(self):
        self.name = "Outpouring of Life"
        self.tags = [Level.Tags.Nature, Level.Tags.Enchantment]
        self.level = 7
        self.max_charges = 1

        self.max_channel = 5

        self.range = 0
        self.radius = 6

        self.sacrifice_damage = 0
        self.duration = 0 # for vital extension

        self.upgrades['shaped'] = (1, 5, "Lifescourge", "Enemies in the radius are poisoned for 20 turns and take 18 [dark] damage for each ally in the radius.")
        self.upgrades['extend'] = (1, 5, "Vital Extension", "Any positive effects on allies in the radius are extended by this spell's max channel, plus half of this spell's duration bonuses.")
        self.add_upgrade(SelfSacrifice())

    def get_description(self):
        return ("Channel the area's life force for [{max_channel}_turns:duration].\n"
                "When channeling is complete, all allies in a 6 tile radius become [living], are cleansed of debuffs, and regenerate a fixed 12 HP each turn for 10 turns.").format(**self.fmt_dict())

    def cast(self, x, y, channel_cast=False):
        if not channel_cast:
            chn = Level.ChannelBuff(self.cast, self.caster)
            self.owner.apply_buff(chn, self.get_stat('max_channel'))
            return
        
        if not self.owner.has_buff(Level.ChannelBuff):
            num_allies = len([u for u in self.owner.level.get_units_in_ball(self.owner, self.get_stat('radius')) if not Level.are_hostile(self.owner, u)])
            for u in self.owner.level.get_units_in_ball(self.owner, self.get_stat('radius')):
                if Level.are_hostile(u, self.owner):
                    if self.get_stat('shaped'):
                        u.deal_damage(18*num_allies, Level.Tags.Dark, self)
                        u.apply_buff(CommonContent.Poison(), 20)
                else:
                    if u == self.caster:
                        continue
                    if Level.Tags.Living not in u.tags:
                        u.tags.append(Level.Tags.Living)
                    for b in u.buffs:
                        if b.buff_type == Level.BUFF_TYPE_CURSE:
                            u.remove_buff(b)
                        elif b.buff_type == Level.BUFF_TYPE_BLESS and self.get_stat('extend') and b.turns_left:
                            b.turns_left += self.get_stat('max_channel') + (self.get_stat('duration') - self.duration)
                    if num_allies and self.owner.has_buff(SelfSacrifice):
                        to_add = self.sacrifice_damage // num_allies
                        u.max_hp += to_add
                    u.apply_buff(CommonContent.RegenBuff(12), 10)
        yield

class PortalBuster(Level.Spell):
    def on_init(self):
        self.name = "Rift Ripper"
        self.max_charges = 2
        self.range = 50
        self.tags = [Level.Tags.Arcane, Level.Tags.Sorcery]
        self.level = 8
        self.requires_los = False
        self.radius = 12
        self.damage = 133

        self.upgrades['grab'] = (1, 6, "Grab Ripper", "If you cast this spell on the first turn of the realm, the equipment chest, ruby heart, or scroll in that portal will spawn on the portal's tile.")
        self.upgrades['conserve'] = (1, 4, "Reconstructor", "The portal has a 20% chance to not be destroyed when casting this spell on it.")
        self.upgrades['super'] = (1, 5, "Harness Dimensions", "This spell does an extra hit of damage.")

    def can_cast(self, x, y):
        return type(self.caster.level.tiles[x][y].prop) == Level.Portal

    def get_description(self):
        return (
            "Destroy target portal, then deal [{damage}_arcane_damage:arcane] to enemies in a [{radius}-tile_radius:radius]."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        for p in [p for p in self.owner.level.get_points_in_ball(x, y, self.get_stat('radius'))]:
            for _ in 1+self.get_stat('super'):
                self.caster.level.deal_damage(p.x, p.y, self.get_stat('damage'), Level.Tags.Arcane, self)
        offer = self.caster.level.tiles[x][y].prop.level_gen_params.shrine
        if not (self.get_stat('conserve') and random.random() < .2):
            self.caster.level.tiles[x][y].prop = None
        if self.get_stat('grab') and self.caster.level.turn_no == 1:
            offer.x = x
            offer.y = y
            self.caster.level.props.append(offer)
            offer.level = self.caster.level
            self.caster.level.tiles[x][y].prop = offer

class WasherReflect(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Freshly Washed"
        self.color = Level.Tags.Glass.color
        self.owner_triggers[Level.EventOnDamaged] = self.reflect
        self.resists[Level.Tags.Arcane] = 50
        self.resists[Level.Tags.Dark] = 25
        self.resists[Level.Tags.Holy] = 25

    def reflect(self, evt):
        victim = evt.source if type(evt.source) == Level.Unit else evt.source.owner
        refl = math.ceil(.3*evt.damage)
        victim.deal_damage(refl, evt.damage_type, self)

class Dishwasher(Level.Spell):
    def on_init(self):
        self.name = "Purple Dishwasher"
        self.max_charges = 3
        self.range = 6
        self.requires_los = False
        self.tags = [Level.Tags.Arcane, Level.Tags.Conjuration, Level.Tags.Metallic]
        self.level = 4
        self.must_target_walkable = self.must_target_empty = True
        self.minion_health = 33
        self.minion_damage = 8
        self.minion_range = 2

        self.upgrades['scrub'] = (1, 4, "Soulscrub", "The dishwasher's melee attacks permanently remove 20 [physical] resistance and all buffs on the target.")
        self.upgrades['muck'] = (1, 7, "Grime Engine", "The dishwasher can cast your Slime Form on a 20 turn cooldown.")
        self.upgrades['expel'] = (1, 5, "Expel Dishes", "The dishwasher's melee is replaced by a physical bolt with range equal to double this spell's minion range.")

    def get_extra_examine_tooltips(self):
        return [self.washer()] + self.spell_upgrades

    def get_description(self):
        return (
            "Summon a purple dishwasher."
        ).format(**self.fmt_dict())
    
    def washer(self):
        w = Level.Unit()
        w.max_hp = self.get_stat('minion_health')
        w.name = "Purple Dishwasher"
        w.asset_name = "void_slime"
        m = CommonContent.SimpleCurse(WasherReflect, 10, Level.Tags.Thunderstrike)
        m.name = "Dishwash"
        m.can_cast = lambda x, y: CommonContent.SimpleCurse.can_cast(m, x, y) and Level.Tags.Metallic in self.caster.level.get_unit_at(x, y).tags
        m.cool_down = 5
        m.description = "A [metallic] ally gains 50 [arcane] resist, 25 [dark] and [holy] resist, and reflects 30% of the damage it takes back to the source rounded up for 10 turns"
        d = CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage')) if not self.get_stat('expel') else CommonContent.SimpleRangedAttack(name="Throw Dishes", damage=self.get_stat('minion_damage'), range=self.get_stat('minion_range')*2, damage_type=Level.Tags.Physical)
        if self.get_stat('scrub'):
            def inner_onhit(c, t):
                t.resists[Level.Tags.Physical] -=20
                for b in t.buffs:
                    if b.buff_type == Level.BUFF_TYPE_BLESS:
                        t.remove_buff(b)
            d.onhit = inner_onhit
            d.description = "Permanently removes 20 [physical] resist and removes any active positive effects."
        w.spells = [m, d]
        if self.get_stat('muck'):
            s = Spells.SlimeformSpell()
            s.statholder = self.caster
            s.owner = s.caster = w
            s.cool_down = 20
            w.spells.insert(0, s)
        w.tags = [Level.Tags.Arcane, Level.Tags.Metallic, Level.Tags.Sorcery]
        return w

    def cast_instant(self, x, y):
        self.summon(self.washer(), Level.Point(x, y))


class CrystalModeBuff(Level.Stun):
    def __init__(self, spell):
        Level.Stun.__init__(self)
        self.spell = spell
        self.name = "Crystal Form"
        self.color = Level.Tags.Glass.color
        self.owner_triggers[Level.EventOnPreDamaged] = self.reflect

    def on_applied(self, owner):
        self.caster = self.owner
        if self.spell.get_stat('night'):
            s = self.caster.get_or_make_spell(Spells.NightmareSpell)
            self.owner.level.act_cast(self.owner, s, self.owner.x, self.owner.y, pay_costs=False)

    def reflect(self, evt):
        self.owner.add_shields(1)
        victim = evt.source if type(evt.source) == Level.Unit else evt.source.owner
        refl = math.ceil((1.2+self.spell.get_stat('power'))*evt.damage)
        if self.spell.get_stat('kalei'):
            alltypes =  [Level.Tags.Arcane, Level.Tags.Poison, Level.Tags.Holy, Level.Tags.Dark, Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Physical]
            minres = [dt for dt in alltypes if victim.resists[dt] < 100]
            for _ in range(refl):
                victim.deal_damage(1, random.choice(minres), self.spell)
        else:
            victim.deal_damage(refl, evt.damage_type, self.spell)

class CrystalMode(Level.Spell):
    def on_init(self):
        self.name = "Crystal Form"
        self.max_charges = 1
        self.range = 0
        self.tags = [Level.Tags.Arcane, Level.Tags.Enchantment, Level.Tags.Metallic]
        self.level = 7
        self.duration = 5

        self.upgrades['power'] = (.6, 4, "Extra Sheen", "Reflect another 60% of that damage, for a total of 180% reflection.")
        self.upgrades['kalei'] = (1, 5, "Kaleidoscopic Mirror", "Instead of dealing 1 hit of damage, deal that many hits of 1 damage, chosen randomly from damage types the target is not immune to.")
        self.upgrades['night'] = (1, 5, "Bad Dream", "Automatically cast your Nightmare Aura when casting this spell.")

    def get_description(self):
        return (
            "Assume a crystalline form for [{duration}_turns:duration].\n"
            "You become immobile and your resistances do not change, but you gain [1_SH:shield] whenever you would take damage.\n"
            "Whenever a source attempts to deal damage to you, reflect 120% of that damage back to the source rounded up, calculated before your resistances."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        self.caster.apply_buff(CrystalModeBuff(self), self.get_stat('duration'))


class IceShiv(Level.Spell):
    def on_init(self):
        self.name = "In Cold Blood"
        self.max_charges = 2
        self.damage = 34
        self.range = 50
        self.hp_cost = 15
        self.requires_los = False
        self.tags = [Level.Tags.Ice, Level.Tags.Blood, Level.Tags.Sorcery]
        self.level = 5

        self.upgrades['clean'] = (1, 4, "Clean Kill", "This spell's hits deal double damage if they would kill the target with doubled damage.")
        self.upgrades['animate'] = (1, 6, "Cryoanimation", "If a unit would die to this spell's [ice] hit, summon an icy dancing blade at the target's location.")
        self.upgrades['bust'] = (1, 3, "Armor Buster", "Hit targets permanently lose all [physical] resist.")

    def can_cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        return Level.Spell.can_cast(self, x, y) and u and not self.caster.level.can_see(self.caster.x, self.caster.y, x, y)
    
    def animator(self):
        wep = BossSpawns.apply_modifier(BossSpawns.Icy, Monsters.DancingBlade())
        CommonContent.apply_minion_bonuses(self, wep)
        return wep

    def get_extra_examine_tooltips(self):
        return self.spell_upgrades[:2] + [self.animator(), self.spell_upgrades[2]]

    def get_description(self):
        return (
            "Rush target enemy with a bloody icicle, dealing [{damage}_ice_damage:ice], plus the same amount of [physical] damage if the enemy is more than 10 tiles away.\n"
            "Can only be used on targets outside of your line of sight."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        adj = list(self.caster.level.get_adjacent_points(Level.Point(x, y), True, True))
        adj.sort(key=lambda x: Level.distance(self.caster, x))
        pot = adj[0]
        kill_dist = Level.distance(u, self.caster)
        self.caster.level.act_move(self.caster, pot.x, pot.y, teleport=True)
        if self.get_stat('bust'):
            u.resists[Level.Tags.Physical] = min(u.resists[Level.Tags.Physical], 0)
        d = self.get_stat('damage')
        multiplier = (100 - u.resists[Level.Tags.Ice]) / 100.0
        icy_thres = int(math.ceil(d*multiplier))
        print(icy_thres)
        to_beat = icy_thres*2
        d *= (2 if self.get_stat('clean') and to_beat >= u.cur_hp else 1)
        u.deal_damage(d, Level.Tags.Ice, self)
        if u.cur_hp <= 0 and self.get_stat('animate'):
            self.summon(self.animator(), u)
        if kill_dist >= 10:
            multiplier = (100 - u.resists[Level.Tags.Physical]) / 100.0
            to_beat = int(math.ceil(d*multiplier))*2
            if self.get_stat('clean') and to_beat >= u.cur_hp:
                d *= 2
            u.deal_damage(d, Level.Tags.Physical, self)

class BloodElectroBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.name = "Lightning Counter"
        self.color = Level.Tags.Blood.color
        self.owner_triggers[Level.EventOnPreDamaged] = self.counter

    def on_pre_advance(self):
        if self.spell.get_stat('anger'):
            mod = 3*((self.owner.max_hp-self.owner.cur_hp)//15)
            self.tag_bonuses[Level.Tags.Lightning]['damage'] = mod

    def counter(self, evt):
        if evt.damage < 6:
            return
        source = evt.source if type(evt.source) == Level.Unit else evt.source.owner
        if not source or source not in self.owner.level.get_units_in_los(self.owner):
            return
        lb = self.owner.get_or_make_spell(Spells.LightningBoltSpell)
        if lb.can_cast(source.x, source.y):
            self.owner.level.act_cast(self.owner, lb, source.x, source.y, pay_costs=False)
        if self.spell.get_stat('storm') and (cloud := self.owner.level.tiles[self.owner.x][self.owner.y].cloud):
            if isinstance(cloud, CommonContent.StormCloud):
                storm_spell = self.owner.get_or_make_spell(Spells.ThunderStrike)
            elif isinstance(cloud, CommonContent.BlizzardCloud):
                storm_spell = self.owner.get_or_make_spell(Spells.Iceball)
            if storm_spell.can_cast(source.x, source.y):
                self.owner.level.act_cast(self.owner, storm_spell, source.x, source.y, pay_costs=False)
        if (Level.Tags.Demon in source.tags or Level.Tags.Undead in source.tags) and self.spell.get_stat('heaven'):
            hb = self.owner.get_or_make_spell(Spells.HolyBlast)
            if hb.can_cast(source.x, source.y):
                self.owner.level.act_cast(self.owner, hb, source.x, source.y, pay_costs=False)

class BloodElectro(Level.Spell):
    def on_init(self):
        self.name = "Bloodspark"
        self.max_charges = 3
        self.range = 0
        self.tags = [Level.Tags.Lightning, Level.Tags.Blood, Level.Tags.Enchantment]
        self.level = 6
        self.hp_cost = 33
        self.duration = 18

        self.upgrades['storm'] = (1, 5, "Tempest Counter", "Additionally counter with your Thunder Strike if you're standing in a storm cloud, or your Iceball if you're standing in a blizzard.")
        self.upgrades['heaven'] = (1, 4, "Heavens' Parry", "Additionally counter with your Heavenly Blast if the enemy has [demon] or [undead].")
        self.upgrades['anger'] = (1, 6, "Anger The Storm", "While this buff is active, gain 3 damage for [lightning] spells and skills for every 15 missing HP.")

    def get_description(self):
        return (
            "Whenever you take 6 or more damage from an enemy in line of sight, counterattack with your Lightning Bolt spell for free.\n"
            "Lasts [{duration}_turns:duration]"
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        self.caster.apply_buff(BloodElectroBuff(self), self.get_stat('duration'))

class InsuranceBuff(Level.Buff):

    def __init__(self, summoner):
        Level.Buff.__init__(self)
        self.summoner = summoner

    def on_init(self):
        self.name = "Insurance"
        self.color = Level.Tags.Dark.color
        self.owner_triggers[Level.EventOnDeath] = self.on_death

    def on_death(self):
        self.summoner.deal_damage(-25, Level.Tags.Heal, self)

class FaePact(Level.Spell):
    def on_init(self):
        self.name = "Arcanist's Bloodpact"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Arcane, Level.Tags.Blood, Level.Tags.Conjuration]
        self.level = 7
        self.minion_health = 0
        self.hp_cost = 30

        self.upgrades['pro'] = (1, 5, "Pact of Progress", "This spell will exclusively summon higher-power wizards.")
        self.upgrades['insured'] = (1, 3, "Wizard Insurance", "The Wizard heals for 25 HP if the summoned wizard dies within 20 turns.")
        self.upgrades['brave'] = (1, 5, "Bond of Bravery", "The summoned wizard gains a random extra modifier if it's the first turn of the realm.")

    def get_description(self):
        return (
            "Summon a random wizard with the fae modifier to help you in battle."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        base_wizards = [tup[0] for tup in RareMonsters.all_wizards]
        if self.get_stat('pro'):
            base_wizards = base_wizards[(len(base_wizards)//2):]
        wizard_pool = base_wizards + [RareMonsters.MoonMage, RareMonsters.BloodWizard, RareMonsters.ChaosWizard, RareMonsters.DeathchillWizard]
        wiz = random.choice(wizard_pool)()
        BossSpawns.apply_modifier(BossSpawns.Faetouched, wiz)
        if self.owner.level.turn_no == 1 and self.get_stat('brave'):
            mod = random.choice([tup[0] for tup in BossSpawns.modifiers])
            BossSpawns.apply_modifier(mod, wiz)
        CommonContent.apply_minion_bonuses(self, wiz)
        self.summon(wiz, self.caster)
        if self.get_stat('insured'):
            wiz.apply_buff(InsuranceBuff(self.caster), 20)

class WallToss(Level.Spell):
    def on_init(self):
        self.name = "Wall Kinesis"
        self.max_charges = 17
        self.tags = [Level.Tags.Nature, Level.Tags.Sorcery]
        self.range = 6
        self.level = 2
        self.damage = 20
        self.can_target_empty = False

        self.upgrades['crush'] = (1, 4, "Crush Wall", "This spell deals another hit of double damage to targets with at most 100 HP.")
        self.upgrades['requires_los'] = (-1, 2, "Blindcasting", "Wall Kinesis no longer requires line of sight.")
        self.upgrades['runic'] = (1, 3, "Runic Stone", "This spell also deals [arcane] damage.")

    def get_description(self):
        return (
            "Throw an adjacent wall at the target, dealing [{damage}_physical_damage:damage]."
        ).format(**self.fmt_dict())

    def can_cast(self, x, y):
        has_walls = any(self.caster.level.tiles[i.x][i.y].is_wall() for i in self.caster.level.get_adjacent_points(self.caster, False, False))
        return Level.Spell.can_cast(self, x, y) and has_walls
    
    def cast(self, x, y):
        if any(self.caster.level.tiles[i.x][i.y].is_wall() for i in self.caster.level.get_adjacent_points(self.caster, False, False)):
            adj_walls = [i for i in self.caster.level.get_adjacent_points(self.caster, False, False) if self.caster.level.tiles[i.x][i.y].is_wall()]
            adj_walls.sort(key=lambda x: Level.distance(x, self.caster))
            used = adj_walls[0]
            self.caster.level.make_floor(used.x, used.y)
            u = self.caster.level.get_unit_at(x, y)
            if not u:
                return
            u.deal_damage(self.get_stat('damage'), Level.Tags.Physical, self)
            if self.get_stat('crush') and u.hp <= 100:
                u.deal_damage(self.get_stat('damage')*2, Level.Tags.Physical, self)
            elif self.get_stat('runic'):
                u.deal_damage(self.get_stat('damage'), Level.Tags.Arcane, self)
            yield

class ClayizeBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnUnitAdded] = self.clayize
        self.color = Level.Color(160, 135, 126)
        self.name = "Earthen Force"
        self.stack_type = Level.STACK_DURATION

    def clayize(self, evt):
        hp_boost = False
        if Level.are_hostile(evt.unit, self.owner) or evt.unit == self.owner or evt.unit.source == self.spell:
            return
        turns_removed = max(3, math.ceil(evt.unit.max_hp*.2))
        if self.turns_left >= 50:
            hp_boost = True
        if turns_removed > self.turns_left:
            self.owner.deal_damage(6*self.turns_left, Level.Tags.Physical, self.spell)
        else:
            self.turns_left -= turns_removed
            BossSpawns.apply_modifier(BossSpawns.Claytouched, evt.unit)
            if hp_boost and self.spell.get_stat('unearth'):
                evt.unit.max_hp = math.ceil(evt.unit.max_hp*1.6)
                evt.unit.cur_hp = evt.unit.max_hp
            elif self.spell.get_stat('relic') and random.random() < .2:
                BossSpawns.apply_modifier(BossSpawns.Claytouched, evt.unit)
            for b in evt.unit.buffs:
                if not b.applied:
                    b.apply(evt.unit)
                    b.buff_type = Level.BUFF_TYPE_PASSIVE

class Clayize(Level.Spell):
    def on_init(self):
        self.name = "Force of Upheaval"
        self.max_charges = 1
        self.tags = [Level.Tags.Nature, Level.Tags.Arcane, Level.Tags.Enchantment]
        self.range = 0
        self.level = 6
        self.radius = 7

        self.upgrades['fossil'] = (1, 4, "Raise Fossils", "If you gain 30 or more turns of Earthen Force from a single cast of this spell, summon 8 clay minions for free. These are chosen randomly from pachyderms, small worm balls, ice lizards, and fire lizards.")
        self.upgrades['unearth'] = (1, 5, "Greater Melding", "If you would summon an ally with 50 or more turns of Earthen Force remaining, that ally's maximum HP increases by 25%.")
        self.upgrades['relic'] = (1, 6, "Quest for the Grail", "Each ally you summon that is successfully affected by Earthen Force has a 20% chance to additionally gain [immortal:holy]")

    def get_description(self):
        return (
            "Destroy all walls in a [{radius}-tile_radius:radius].\n"
            "For each wall destroyed, gain 1 turn of Earthen Force.\n"
            "Whenever an ally would be summoned, except by this spell, consume a number of turns equal to 3 or 20% of the unit's max HP rounded up, whichever is greater and add the [clay:physical] modifier to it.\n"
            "If that amount of turns cannot be consumed, the buff is removed and you take a fixed 6 [physical] damage per remaining turn of Earthen Force instead.\n"
        ).format(**self.fmt_dict())

    def get_extra_examine_tooltips(self):
        return [self.spell_upgrades[0]] + [BossSpawns.apply_modifier(BossSpawns.Claytouched, i()) for i in [Monsters.Elephant, Monsters.WormBall, Monsters.IceLizard, Monsters.FireLizard]] + self.spell_upgrades[1:]
    
    def cast_instant(self, x, y):
        cur_destroyed_walls = 0
        for p in [p for p in self.owner.level.get_points_in_ball(x, y, self.get_stat('radius'))]:
            if self.caster.level.tiles[p.x][p.y].is_wall():
                self.caster.level.make_floor(p.x, p.y)
                cur_destroyed_walls += 1
        if cur_destroyed_walls > 0:
            self.caster.apply_buff(ClayizeBuff(self), cur_destroyed_walls)
        if cur_destroyed_walls >= 30 and self.get_stat('fossil'):
            for _ in range(8):
                fossil_mon = BossSpawns.apply_modifier(BossSpawns.Claytouched, random.choice([Monsters.Elephant, Monsters.WormBall, Monsters.IceLizard, Monsters.FireLizard])())
                CommonContent.apply_minion_bonuses(self, fossil_mon)
                self.summon(fossil_mon, self.caster)

class ApepGrasp(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.owner_triggers[Level.EventOnDeath] = self.on_death
        self.owner_triggers[Level.EventOnBuffApply] = self.check
        self.owner_triggers[Level.EventOnUnitAdded] = self.reset_incarni
        self.reincarns_consumed = 0
        self.color = Level.Tags.Chaos.color
        self.name = "Chaos Curse"

    def strip_reincarns(self):
        if self.owner.has_buff(CommonContent.ReincarnationBuff):
            reincarn = self.owner.get_buff(CommonContent.ReincarnationBuff)
            self.reincarns_consumed += reincarn.lives
            self.owner.remove_buff(reincarn)

    def reset_incarni(self, evt):
        self.first_snake = True

    def on_applied(self, owner):
        self.strip_reincarns()
    
    def check(self, evt):
        self.strip_reincarns()

    def on_death(self, evt):
        total = self.owner.max_hp + 17*(self.reincarns_consumed*(1+self.spell.get_stat('lod')))
        if total < 21:
            return
        while total > 0:
            u = self.spell.child()
            if self.spell.get_stat('dark') and any(t in self.owner.tags for t in [Level.Tags.Demon, Level.Tags.Undead]):
                u = random.choice([self.spell.icechild(), self.spell.ghostchild()])
            self.summon(u, self.owner)
            total -= 17

    def get_tooltip(self):
        return "On death, splits into chaos snakes based on max HP. Loses all reincarnations and cannot gain reincarnations.\nCurrent number of consumed reincarnations: %d" % self.reincarns_consumed

class ApepPop(Level.Spell):
    def on_init(self):
        self.name = "Grasp of Apep"
        self.max_charges = 2
        self.tags = [Level.Tags.Chaos, Level.Tags.Enchantment, Level.Tags.Conjuration]
        self.range = 6
        self.level = 4

        self.level_last_cast = -1

        basis = lambda: BossSpawns.apply_modifier(BossSpawns.Chaostouched, Monsters.Snake())
        self.child = lambda: self.sourceify(basis())
        self.faechild = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Faetouched, basis()))
        self.icechild = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Icy, basis()))
        self.ghostchild = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Ghostly, basis()))
        ex = self.child()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[1].damage
        self.minion_range = ex.spells[0].range

        self.upgrades['lod'] = (1, 4, "Of Life and Death", "Consumed reincarnations add another extra snake.")
        self.upgrades['dark'] = (1, 4, "Conquer the Underworld", "If Grasp of Apep is cast on a [undead] or [demon] unit, all snakes resulting from that unit's death gain either [icy:ice] or ghostly randomly.")
        self.upgrades['incarni'] = (1, 4, "Avatar of Apep", "The first time you cast Grasp of Apep each realm, summon the Avatar of Apep near yourself.")

    def can_cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        return u and not Level.are_hostile(u, self.owner) and Level.Spell.can_cast(self, x, y) and u.source != self

    def get_description(self):
        return (
            "Target ally loses all reincarnations it has and cannot gain new ones.\n"
            "Whenever it dies, summon chaos snakes around it based on its maximum HP.\n"
            "Consumed reincarnations add an additional snake each.\n"
            "Cannot target allies summoned by this spell."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.child(), self.spell_upgrades[0], self.spell_upgrades[1], self.icechild(), self.ghostchild(), self.spell_upgrades[2], self.avatar()]
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        u.apply_buff(ApepGrasp(self))
        if self.level_last_cast != self.caster.level.level_no:
            self.level_last_cast = self.caster.level.level_no
            if self.get_stat('incarni'):
                self.summon(self.avatar(), self.caster)

    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def avatar(self):
        avatar_x = BossSpawns.apply_modifier(BossSpawns.Immortal, BossSpawns.apply_modifier(BossSpawns.Chaostouched, Variants.SnakeGiant()))
        avatar_x.name = "Avatar of Apep"
        self.sourceify(avatar_x)
        return avatar_x
    
class PredestinedBuff(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.reincarns_consumed = 0
        self.color = Level.Tags.Dark.color
        self.name = "Predestiny"
    
    def on_unapplied(self):
        if Level.Tags.Holy in self.owner.tags:
            self.owner.deal_damage(-(math.ceil(self.owner.cur_hp/2)), Level.Tags.Heal, self.spell) if not self.spell.get_stat('heresy') else self.owner.deal_damage(math.ceil(self.owner.cur_hp/2), Level.Tags.Dark, self.spell)
        elif any(t in self.owner.tags for t in [Level.Tags.Demon, Level.Tags.Undead]):
            self.owner.deal_damage(math.ceil(self.owner.cur_hp/2), Level.Tags.Holy, self.spell) if not self.spell.get_stat('heresy') else self.owner.deal_damage(-(math.ceil(self.owner.cur_hp/2)), Level.Tags.Heal, self.spell)
        elif Level.Tags.Arcane in self.owner.tags and self.spell.get_stat('persecute'):
            self.owner.deal_damage(math.ceil(self.owner.cur_hp/2), Level.Tags.Holy, self.spell)
        elif any(t in self.owner.tags for t in [Level.Tags.Living, Level.Tags.Nature]):
            if self.spell.get_stat('mercy'):
                self.owner.deal_damage(-(math.ceil(self.owner.cur_hp/2)), Level.Tags.Heal, self.spell)
            elif self.spell.get_stat('persecute'):
                self.owner.deal_damage(math.ceil(self.owner.cur_hp/2), Level.Tags.Holy, self.spell)
            if random.random() < .5:
                self.owner.deal_damage(-(math.ceil(self.owner.cur_hp/2)), Level.Tags.Heal, self.spell)
            else:
                self.owner.deal_damage(math.ceil(self.owner.cur_hp/2), Level.Tags.Holy, self.spell)

class Predestine(Level.Spell):
    def on_init(self):
        self.name = "Predestination"
        self.max_charges = 2
        self.tags = [Level.Tags.Holy, Level.Tags.Enchantment, Level.Tags.Dark]
        self.range = 10
        self.level = 5
        self.can_target_empty = False
        self.requires_los = False

        self.upgrades['mercy'] = (1, 2, "Mercy", "[Living] and [nature] units are always healed.")
        self.upgrades['heresy'] = (1, 2, "Heresy", "[Holy] units take [dark] damage, while [demon] and [undead] units are healed.")
        self.upgrades['persecute'] = (1, 3, "Persecution", "[Living] and [nature] units are always damaged. [Arcane] units become targetable and also always take damage.")

    def get_description(self):
        return (
            "After 4 turns, the target is affected depending on its unit type.\n"
            "[Holy] units heal for half of their current HP, while [demon] and [undead] units take that much [holy] damage.\n"
            "[Living] and [nature] units randomly experience one of these two effects.\n"
            "Other units are unaffected."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        u.apply_buff(PredestinedBuff(self), 4)

class SlowTaxBuff(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.consecutive_casts = 0
        self.color = Level.Tags.Arcane.color
        self.name = "Price of Waiting"

    def on_advance(self):
        if not self.owner.is_alive():
            self.owner.remove_buff(self)
        elif type(self.owner.get_ai_action()) != Level.CastAction:
            self.owner.deal_damage(self.spell.get_stat('damage'), Level.Tags.Arcane, self.spell)
            self.consecutive_casts = 0
        else:
            self.consecutive_casts += 1
            if self.consecutive_casts % 3 == 0 and self.spell.get_stat('collect'):
                for _ in range(2):
                    self.spell.summon(self.spell.collector(), self.owner)
                    self.owner.apply_buff(Level.Stun(), 3)
                    pass
    
class DefenderTax(Upgrades.Upgrade):

    def on_init(self):
        self.prereq = SlowTax
        self.name = "Defense Investment"
        self.level = 5
        self.description = "Gain [1_SH:shield] the first time a unit takes damage from this spell each turn, to a maximum of 5."
        self.global_triggers[Level.EventOnDamaged] = self.shield
        self.owner_triggers[Level.EventOnUnitAdded] = self.reset
        self.has_triggered = False

    def reset(self, evt):
        self.has_triggered = False

    def shield(self, evt):
        if type(evt.source) == type(self.prereq) and not self.has_triggered and self.owner.shields < 5:
            self.owner.level.player_unit.add_shields(1)
            self.has_triggered = True

class SlowTax(Level.Spell):
    def on_init(self):
        self.name = "Hesitation Tax"
        self.max_charges = 2
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane]
        self.range = 7
        self.level = 5
        self.damage = 15
        self.can_target_empty = False

        self.upgrades['damage'] = (10, 2, "Tax Hike")
        self.add_upgrade(DefenderTax())
        self.upgrades['collect'] = (1, 7, "Collections Department", "Whenever a unit affected by this spell casts spells for 3 turns in a row, stun it for 3 turns and summon two chaos fae queens near it.")

    def get_extra_examine_tooltips(self):
        return self.spell_upgrades[:2] + [self.collector(), self.spell_upgrades[2]] 

    def get_description(self):
        return (
            "Target unit takes [{damage}_arcane_damage:arcane] whenever it ends its turn without casting a spell."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        u.apply_buff(SlowTaxBuff(self))
    
    def collector(self):
        base = BossSpawns.apply_modifier(BossSpawns.Chaostouched, Monsters.ThornQueen())
        CommonContent.apply_minion_bonuses(self, base)
        base.name = "Tax Collector"
        return base

class MindTaxBuff(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.consecutive_casts = 0
        self.color = Level.Tags.Arcane.color
        self.name = "Mental Oppression"

    def on_advance(self):
        buff_bonus = len(self.owner.buffs)
        if not self.spell.get_stat('pow'):
            buff_bonus = len([b for b in self.owner.buffs if b.buff_type == Level.BUFF_TYPE_BLESS])
        cd_bonus = sum(s.cool_down for s in self.owner.spells)
        total = self.spell.get_stat('damage') + buff_bonus + cd_bonus
        self.owner.deal_damage(total, random.choice([Level.Tags.Arcane, Level.Tags.Dark]), self.spell)

class MindTax(Level.Spell):
    def on_init(self):
        self.name = "Overwhelm Mind"
        self.max_charges = 2
        self.tags = [Level.Tags.Dark, Level.Tags.Enchantment, Level.Tags.Arcane]
        self.range = 8
        self.level = 5
        self.damage = 7
        self.can_target_empty = False
        self.requires_los = False

        self.upgrades['violent'] = (1, 3, "Violent Suggestion", "The target is also permanently berserked.")
        self.upgrades['kn'] = (1, 4, "Knowledge Tax", "All of the target's spell cooldowns are increased by 1 before this effect is applied")
        self.upgrades['pow'] = (1, 4, "Power Tax", "The bonus damage of this spell from buffs also counts debuffs and passive effects")

    def get_description(self):
        return (
            "Target unit takes [{damage}:damage] [arcane] or [dark] damage, plus the sum of its spell cooldowns and the number of buffs it has."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        u.apply_buff(MindTaxBuff(self))
        if self.get_stat('violent'):
            u.apply_buff(Level.BerserkBuff())
        if self.get_stat('kn'):
            for s in u.spells:
                if s.cool_down > 0:
                    s.cool_down += 1

class ScalyBreath(Monsters.BreathWeapon):

    def on_init(self):
        self.name = "Scale Shot"
        self.damage = 10
        self.damage_type = [Level.Tags.Physical]

    def get_description(self):
        return "Shoots a cone of scales, dealing %d physical damage" % self.damage

    def per_square_effect(self, x, y):
        self.caster.level.deal_damage(x, y, self.damage, random.choice(self.damage_type), self)
        self.caster.resists[Level.Tags.Physical] -= 1

class ScaleThorn(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.name = "Thorns"
        self.color = Level.Tags.Physical.color
        self.resists[Level.Tags.Physical] = 50
        self.buff_type = Level.BUFF_TYPE_BLESS

    def on_init(self):
        self.global_triggers[Level.EventOnSpellCast] = self.on_spell
        self.owner_triggers[Level.EventOnPreDamaged] = self.mirror
        self.owner_triggers[Level.EventOnDamaged] = self.adapt

    def on_applied(self, owner):
        if self.spell.get_stat('shot'):
            sp = ScalyBreath()
            sp.cool_down = 3
            sp.owner = sp.caster = owner
            sp.damage = 2*self.spell.get_stat('damage')
            sp.range = 6
            owner.spells.insert(0, sp)

    def on_spell(self, evt):
        if evt.x != self.owner.x or evt.y != self.owner.y:
            return
        if not (isinstance(evt.spell, CommonContent.LeapAttack) or evt.spell.melee):
            return
        self.owner.level.queue_spell(self.do_thorns(evt.caster))

    def do_thorns(self, unit):
        unit.deal_damage(self.spell.get_stat('damage'), Level.Tags.Physical, self.spell)
        yield

    def mirror(self, evt):
        if self.spell.get_stat('mir'):
            aggressor = evt.source.owner if type(evt.source) != Level.Unit else evt.source
            if Level.Point(aggressor.x, aggressor.y) in self.owner.level.get_adjacent_points(self.owner, False, False):
                self.owner.add_shields(1)
                aggressor.deal_damage(evt.damage, evt.damage_type, self.spell)

    def adapt(self, evt):
        if self.spell.get_stat('adapt'):
            self.owner.resists[evt.damage_type] += 15

class RazorScales(Level.Spell):
    def on_init(self):
        self.name = "Scale Armor"
        self.max_charges = 5
        self.tags = [Level.Tags.Enchantment, Level.Tags.Nature]
        self.range = 5
        self.level = 3
        self.damage = 7
        self.can_target_empty = False

        self.upgrades['mir'] = (1, 7, "Mirror Armor", "The target automatically blocks and reflects damage from adjacent sources.")
        self.upgrades['adapt'] = (1, 6, "Adaptive Carapace", "Whenever the target takes damage, it gains 15 resistance to that type permanently.")
        self.upgrades['shot'] = (1, 4, "Scale Shot", "The target gains a cone attack dealing double this spell's retaliation damage with a 3 turn cooldown. This attack reduces the user's [physical] resist by 1 per square it targets.")

    def get_description(self):
        return (
            "Target ally gains melee retaliation dealing [{damage}_physical_damage:physical] and 50 [physical] resist."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        u.apply_buff(ScaleThorn(self))

class StormCycleBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnDeath] = self.get_spirit
        self.color = Level.Tags.Lightning.color
        self.name = "Spirit Storm"
        self.hp_ct = 0

    def get_spirit(self, evt):
        if Level.are_hostile(evt.unit, self.owner) or evt.unit == self.owner or evt.unit.source == self.spell or evt.unit.turns_to_death != 0:
            return
        else:
            spi = self.spell.base()
            if Level.Tags.Arcane in evt.unit.tags and self.spell.get_stat('starry'):
                spi = self.spell.spirit_star()
            if self.spell.get_stat('feeder'):
                spi.buffs.append(Monsters.SpiritBuff(Level.Tags.Lightning))
            self.summon(spi, evt.unit)
            self.hp_ct += evt.unit.max_hp
            while self.hp_ct >= 75:
                mon = self.spell.slime()
                mon.max_hp = round(mon.max_hp, -1)
                self.summon(mon, evt.unit)
                self.hp_ct -= 75

class StormRecycle(Level.Spell):
    def on_init(self):
        self.name = "Spirit Cycle"
        self.max_charges = 2
        self.tags = [Level.Tags.Enchantment, Level.Tags.Conjuration, Level.Tags.Lightning, Level.Tags.Ice]
        self.range = 0
        self.level = 6
        self.duration = 20

        ex = Variants.StormSpirit()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        self.base = lambda: self.sourceify(Variants.StormSpirit())
        self.spirit_star = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Faetouched, Variants.StormSpirit()))
        self.slime = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Stormtouched, Monsters.IceSlime()))

        self.upgrades['starry'] = (1, 4, "Starcycle", "[Arcane] units expiring cause their spirits to gain [fae:arcane].")
        self.upgrades['feeder'] = (1, 3, "Pulse Feed", "Spirits gain HP twice when witnessing [lightning] spells.")
        self.upgrades['collect'] = (1, 5, "Coalescence", "For every 75 HP of units expiring, summon an electric ice slime near the last expired unit, which has its HP rounded to the nearest multiple of 10.")

    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        return m

    def get_description(self):
        return (
            "For [{duration}_turns:duration], whenever a temporary ally's duration expires, summon a storm spirit in its place.\n"
            "This does not affect allies summoned by this spell."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        self.caster.apply_buff(StormCycleBuff(self), self.get_stat('duration'))

class SphinxRiddling(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.color = Level.Tags.Arcane.color
        self.name = "Riddling"
        self.turns = 9
        self.turn_ct = 0
        self.riddle = None #3-tup: riddletype, riddle stats (pos shift for mov riddles, etc), riddle string (for get_tooltip)
        self.unsolved = [] #list of units that have yet to solve the riddle
        self.solved = [] #list of units that solved the riddle
        self.cannot_be_solved = [] #list of units that failed the riddle somehow
        self.pos_log = {} # for movement riddles
        self.global_triggers[Level.EventOnDamaged] = self.check_damage_riddles
        self.global_triggers[Level.EventOnDeath] = self.clean 
        self.global_triggers[Level.EventOnMoved] = self.check_move_riddle

    def check_move_riddle(self, evt):
        if evt.unit not in self.unsolved or not self.riddle:
            return
        if self.riddle[0] == "movement":
            x_diff = evt.unit.x - self.pos_log[evt.unit].x
            y_diff = evt.unit.y - self.pos_log[evt.unit].y
            if x_diff == self.riddle[1][0] and y_diff == self.riddle[1][1]:
                print("unit solved movement riddle")
                self.unsolved.remove(evt.unit)
                self.solved.append(evt.unit)

    def check_damage_riddles(self, evt):
        if not self.riddle:
            return
        if self.riddle[0] == "nodamage":
            if evt.unit in self.unsolved: # unit failed a nodamage riddle
                self.cannot_be_solved.append(evt.unit) #move them to unsolvable
                self.unsolved.remove(evt.unit)
                print("unit failed nodamage riddle")
        if self.riddle[0] == "damagetype":
            if evt.damage_type == self.riddle[1] and evt.damage >= 10: #unit dealt the correct damage type for a damage riddle
                dealer = evt.source if type(evt.source) == Level.Unit else evt.source.owner
                if dealer in self.unsolved:
                    self.unsolved.remove(dealer)
                    self.solved.append(dealer) #move them to solved
                    print("unit passed damage type riddle")
    
    def clean(self, evt):
        for l in [self.unsolved, self.solved, self.cannot_be_solved]:
            try:
                l.remove(evt.unit) #remove dead units from lists for memory efficiency
            except:
                continue

    def gen_riddle(self):
        riddle = []
        self.unsolved = self.solved = self.cannot_be_solved = [] #clean out unit trackers
        self.pos_log = {} # clean position log as well
        riddle_type = random.choice(["movement", "nodamage", "damagetype"])
        riddle.append(riddle_type)
        self.unsolved = [u for u in self.owner.level.get_units_in_los(self.owner)]
        if riddle_type == "movement":
            pos_shifts = [-3, -2, -1, 1, 2, 3] #to exclude 0
            riddle_pos_shift = (random.choice(pos_shifts), random.choice(pos_shifts))
            riddle.append(riddle_pos_shift)
            riddlestr = "Travel %d %s and %d %s." % (abs(riddle_pos_shift[0]), "towards the sky" if riddle_pos_shift[0] > 0 else "towards the depths", abs(riddle_pos_shift[1]), "towards the tomes" if riddle_pos_shift[1] > 0 else "towards the log of worlds")
            riddle.append(riddlestr)
            self.pos_log = {u:Level.Point(u.x, u.y) for u in self.unsolved}
        elif riddle_type == "nodamage":
            riddle.append(self.turns)
            riddle.append("Show me %d nights of peace." % self.turns)
        elif riddle_type == "damagetype":
            dt_words = { #for string builder
                Level.Tags.Lightning: "that which drops from the sky",
                Level.Tags.Fire: "that which scorches all",
                Level.Tags.Ice: "that which makes man shiver",
                Level.Tags.Arcane: "that which perplexes the mind",
                Level.Tags.Dark: "that which obscures",
                Level.Tags.Poison: "that which slowly kills",
                Level.Tags.Holy: "that which is righteous and honest",
                Level.Tags.Physical: "that which is force itself"
            }
            dt = random.choice(list(dt_words.keys()))
            riddle.append(dt)
            riddle.append("Strike with ten or more of %s." % dt_words[dt])
        self.riddle = riddle

    def give_boon(self, unit):
        boonbuff = Level.Buff()
        boonbuff.name = "Boon of the Sphinx"
        boonbuff.stack_type = Level.STACK_INTENSITY
        boonbuff.color = Level.Tags.Construct.color
        possible_attrs = ['damage', 'range', 'radius']
        attr_k = 1 + int(random.random() < .4) + self.spell.get_stat('boons')
        for attr in random.sample(possible_attrs, attr_k):
            magnitude = random.randint(3, 9) #randomize boons
            if attr in ['range', 'radius']:
                magnitude //=3
            boonbuff.global_bonuses[attr] = magnitude
        if random.random() < .5:
            resist_pool = [1]*10 + [2]*6 + [3]*2 + [4]
            resist_tags = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Dark, Level.Tags.Holy, Level.Tags.Arcane]
            for t in random.sample(resist_tags, random.choice(resist_pool)):
                boonbuff.resists[t] = 25*(1+self.spell.get_stat('boons'))
        unit.apply_buff(boonbuff, 10)
    
    def give_bane(self, unit):
        unit.deal_damage(self.spell.get_stat('damage'), Level.Tags.Arcane, self)
        if self.spell.get_stat('rage'):
            unit.deal_damage(self.spell.get_stat('damage'), Level.Tags.Ice, self)
        boonbuff = Level.Buff()
        boonbuff.name = "Bane of the Sphinx"
        boonbuff.stack_type = Level.STACK_INTENSITY
        boonbuff.global_bonuses_pct['damage'] = random.choice([-20, -30, -40, -50])

    def on_pre_advance(self):
        if self.turn_ct % self.turns == 0:
            if self.riddle: #if there is a previous riddle, assign boons and banes
                if self.riddle[0] == "nodamage":
                    self.solved = copy.copy(self.unsolved) #nodamage unsolved automatically "solve" the riddle if they havent already
                    self.unsolved = [] #remove from unsolved to prevent both passing and failing
                for u in self.solved:
                    print("%s passed the riddle" % u.name)
                    self.give_boon(u)
                for u in self.unsolved + self.cannot_be_solved:
                    print("%s failed the riddle" % u.name)
                    if self.spell.get_stat('selective') and not Level.are_hostile(u, self.owner):
                        continue
                    self.give_bane(u)
            self.gen_riddle()

    def on_advance(self):
        self.turn_ct += 1      

    def get_tooltip(self):
        base = "Proposes riddles to units in line of sight. Will reward the clever and punish the foolish."
        if not self.riddle:
            return base
        else:
            base += "\nThe riddle of the sphinx is: %s" % self.riddle[2]
            return base

class SphinxSpell(Level.Spell):
    def on_init(self):
        self.name = "Sphinx"
        self.max_charges = 1
        self.tags = [Level.Tags.Conjuration, Level.Tags.Arcane]
        self.range = 7
        self.level = 5
        self.minion_health = 120
        self.damage = 23
        self.must_target_empty = True

        self.upgrades['selective'] = (1, 4, "Selective Judgment", "The sphinx will not punish allies that fail the riddle.")
        self.upgrades['boons'] = (1, 6, "Greater Boons", "The sphinx's boons provide stronger resist bonuses and can affect 1 extra attribute.")
        self.upgrades['rage'] = (1, 4, "Angry Mind", "The sphinx also deals [ice] damage to units that fail the riddle.")

    def get_description(self):
        return (
            "Summon a sphinx on target tile."
        ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.sphinx()] + self.spell_upgrades
    
    def sphinx(self):
        u = Level.Unit()
        u.max_hp = self.get_stat('minion_health')
        u.name = "Sphinx"
        u.tags = [Level.Tags.Arcane, Level.Tags.Construct]
        u.resists[Level.Tags.Arcane] = 100
        for dt in [Level.Tags.Physical, Level.Tags.Fire, Level.Tags.Lightning]:
            u.resists[dt] = 50
        u.flying = True
        u.stationary = True
        u.asset_name = "blue_lion"
        u.recolor_primary = Level.Tags.Construct.color
        u.buffs.append(SphinxRiddling(self))
        return u
    
    def cast_instant(self, x, y):
        self.summon(self.sphinx(), Level.Point(x, y))

class FunnyBombSpell(Level.Spell):
    def on_init(self):
        self.name = "Super Bomber"
        self.max_charges = 7
        self.tags = [Level.Tags.Conjuration, Level.Tags.Arcane, Level.Tags.Lightning]
        self.range = 7
        self.level = 4
        self.must_target_empty = True
        self.minion_health = 20
        self.radius = 2

        self.upgrades['clustering'] = (1, 5, "Cluster Grenades", "Each bomber now spawns 2 electric void bombers on death.")
        self.upgrades['burner'] = (1, 4, "Double Burst", "The bomber gains [burning:fire] and has five times as much HP.")
        self.upgrades['sneaky'] = (1, 5, "Sneak Attack", "The bomber's leap loses all cooldown and can be used regardless of range or line of sight. The bomber will now instantly explode when moving next to a unit.")

        self.base_bomb = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Stormtouched, BossSpawns.apply_modifier(BossSpawns.Immortal, Variants.VoidBomberGiant())))
        self.baby = lambda: self.sourceify(BossSpawns.apply_modifier(BossSpawns.Stormtouched, Monsters.VoidBomber()))

    def burn(self):
        u = self.base_bomb()
        u.max_hp *= 5
        BossSpawns.apply_modifier(BossSpawns.Flametouched, u)
        return u

    def get_description(self):
        return (
            "Summon an electric immortal void bomber on target tile."
        ).format(**self.fmt_dict())

    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        m.buffs[0].radius = self.get_stat('radius')
        return m

    def get_extra_examine_tooltips(self):
        return [self.base_bomb(), self.spell_upgrades[0], self.baby(), self.spell_upgrades[1], self.burn()]
    
    def cast_instant(self, x, y):
        u = self.base_bomb()
        if self.get_stat('clustering'):
            u.buffs.append(CommonContent.SpawnOnDeath(self.baby, 2))
        elif self.get_stat('burner'):
            u = self.burn()
            u.max_hp *= 5
        elif self.get_stat('sneaky'):
            u.spells[0].range = 99
            u.spells[0].requires_los = False
            u.spells[0].is_ghost = True
            u.spells[0].cool_down = 0
            u.buffs[0].global_triggers[Level.EventOnMoved] = lambda e: u.kill() if any((self.owner.level.get_unit_at(p.x, p.y) not in [u, None]) for p in self.owner.level.get_points_in_ball(u.x, u.y, 1, diag=True)) else None
        self.summon(u, Level.Point(x, y))

class DartMarkBuff(Level.Buff):

    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Marked"
        self.color = Level.Tags.Arcane.color
        self.owner_triggers[Level.EventOnBuffApply] = self.extend_debuff
        self.buff_type = Level.BUFF_TYPE_CURSE

    def extend_debuff(self, evt):
        if evt.buff.buff_type == Level.BUFF_TYPE_CURSE and evt.buff.turns_left != 0:
            evt.buff.turns_left += 2

class RayPierceSpell(Level.Spell):
    def on_init(self):
        self.name = "Exploding Pierce"
        self.max_charges = 10
        self.tags = [Level.Tags.Sorcery, Level.Tags.Metallic, Level.Tags.Fire]
        self.range = 6
        self.level = 3
        self.damage = 20
        self.radius = 2

        self.upgrades['antiwall'] = (1, 4, "Penetration", "The dart passes through walls and deals its [physical] damage twice.")
        self.upgrades['marked'] = (1, 5, "Dart Tag", "All hit units get permanently marked, which increases negative effect duration on them by 2 turns.")

    def get_description(self):
        return (
            "Shoot a magic dart which will travel infinitely in the chosen direction until it hits a wall.\n"
            "Whenever it makes contact with a unit, that unit takes [{damage}_physical_damage:physical].\n"
            "Then, an explosion generated around that unit deals [{damage}_fire_damage:fire] in a [{radius}-tile_radius:radius]."
        ).format(**self.fmt_dict())
    
    #finally, ray targeting
    def get_impacted_tiles(self, x, y):
        start = Level.Point(self.caster.x, self.caster.y)
        dx = (x-self.caster.x)
        dy = (y-self.caster.y)
        result = set()
        for p in Level.Bolt(self.owner.level, start, Level.Point(x+self.owner.level.width*dx, y+self.owner.level.height*dy), False, False):
            if (p.x >= 0 and p.x < self.owner.level.width) and (p.y >= 0 and p.y < self.owner.level.height):
                if self.owner.level.tiles[p.x][p.y].is_wall() and not self.get_stat('antiwall'):
                    break
                if p not in result:
                    result.add(p)
            else:
                break
        return list(result)
    
    def cast(self, x, y):
        aoe = self.get_impacted_tiles(x, y) 
        aoe.sort(key=lambda p: Level.distance(p, self.caster))
        for p in aoe:
            self.caster.level.projectile_effect(p.x, p.y, proj_name='silver_spear', proj_origin=self.caster, proj_dest=aoe[-1])
            if (u := self.caster.level.get_unit_at(p.x, p.y)):
                for _ in range(1+self.get_stat('antiwall')):
                    u.deal_damage(self.get_stat('damage'), Level.Tags.Physical, self)
                    if self.get_stat('marked'):
                        u.apply_buff(DartMarkBuff())
                for p in self.owner.level.get_points_in_ball(u.x, u.y, self.get_stat('radius')):
                    self.owner.level.deal_damage(p.x, p.y, self.get_stat('damage'), Level.Tags.Fire, self)
            yield

class MagicMinigun(Level.Spell):

    def on_init(self):
        self.name = "Arcane Gatling"
        self.range = 7
        self.damage = 8
        self.num_targets = 10
        self.max_charges = 5
        self.tags = [Level.Tags.Metallic, Level.Tags.Sorcery]
        self.can_target_self = False
        self.spool_time = 4
        self.spooling_elapsed = 0

        self.stats.append('spool_time')

        self.upgrades['wide'] = (4, 3, "Improved Swivel", "The gun can target a wider cone.")
        self.upgrades['spool_time'] = (-4, 5, "Auto-Spool", "The gun no longer needs to be spooled in order to fire.")
        self.upgrades['glassgun'] = (1, 5, "Glass Bullets", "Targets are now [glassified:glass] for 1 turn before being hit.")

        self.level = 5

    def get_description(self):
        return (
            "Employ a magic gatling gun to sweep your foes.\n"
            "It must spool up for [{spool_time}_turns:duration] before beginning to fire, but can be channeled infinitely once spooled.\n"
            "Each turn, [{num_targets}:num_targets] bullets are shot at enemies in a cone, dealing [{damage}_physical_damage:damage] each.\n"
        ).format(**self.fmt_dict())

    def get_impacted_tiles(self, x, y):
        divisor = 8-self.get_stat('wide')
        angle = math.pi/divisor
        burst = Level.Burst(self.caster.level, self.caster, self.get_stat('range'), burst_cone_params=Level.BurstConeParams(Level.Point(x, y), angle), expand_diagonals=True)
        return [p for stage in burst for p in stage if self.caster.level.can_see(self.caster.x, self.caster.y, p.x, p.y)]
    
    def cast(self, x, y, channel_cast=False):
        if not channel_cast:
            self.caster.apply_buff(Level.ChannelBuff(self.cast, Level.Point(x, y)))
            self.spooling_elapsed = 0
            return
        else:
            if self.spooling_elapsed < self.get_stat('spool_time') and not self.get_stat('no_spool'):
                self.spooling_elapsed += 1
                return
            possible_targets = [self.caster.level.get_unit_at(p.x, p.y) for p in self.get_impacted_tiles(x, y)]
            possible_targets = [t for t in possible_targets if t and t != self.caster and t.is_alive()]
            if not possible_targets:
                return
            targets = random.choices(possible_targets, k=self.get_stat('num_targets'))
            for t in targets:
                if not t.is_alive():
                    continue
                start = Level.Point(self.caster.x, self.caster.y)
                target = Level.Point(t.x, t.y)
                path = Level.Bolt(self.caster.level, start, target)
                for p in path:
                    self.caster.level.deal_damage(p.x, p.y, 0, Level.Tags.Physical, self)
                    yield
                if self.get_stat('glassgun'):
                    t.apply_buff(CommonContent.GlassPetrifyBuff(), 1)
                self.caster.level.deal_damage(target.x, target.y, self.get_stat('damage'), Level.Tags.Physical, self)


class ParallelT(Level.Spell):

    def on_init(self):
        self.name = "Parallel Test"
        self.range = 8
        self.damage = 1
        self.max_charges = 5
        self.tags = [Level.Tags.Metallic, Level.Tags.Sorcery]

        self.level = 5

    def get_description(self):
        return (
            "Shoot 3 spears in parallel to each other."
        ).format(**self.fmt_dict())
    
    def cast(self, x, y):
        original_line = self.caster.level.get_points_in_line(self.caster, Level.Point(x, y))[1:]

    def get_impacted_tiles(self, x, y):
        lower_line = self.caster.level.get_perpendicular_line(Level.Point(x, y), self.caster, length=4)
        upper_line = self.caster.level.get_perpendicular_line(self.caster, Level.Point(x, y), length=4)
        original_line = self.caster.level.get_points_in_line(self.caster, Level.Point(x, y))[1:]
        #left_line = self.caster.level.get_points_in_line(perp_line[0], Level.Point(x, y))[1:]
        #right_line = self.caster.level.get_points_in_line(perp_line[-1], Level.Point(x, y))[1:]
        left_line = self.caster.level.get_points_in_line(lower_line[0], upper_line[-1])[1:]
        right_line = self.caster.level.get_points_in_line(lower_line[-1], upper_line[0])[1:]
        return original_line+left_line+right_line

class DBeam(Level.Spell):

    def on_init(self):
        self.name = "Delta Beam"
        self.range = 8
        self.damage = 1
        self.max_charges = 5
        self.tags = [Level.Tags.Metallic, Level.Tags.Sorcery]

        self.level = 5

    def get_description(self):
        return (
            "Fire three beams that converge at the target point."
        ).format(**self.fmt_dict())

    def get_impacted_tiles(self, x, y):
        lower_line = self.caster.level.get_perpendicular_line(Level.Point(x, y), self.caster, length=4)
        original_line = self.caster.level.get_points_in_line(self.caster, Level.Point(x, y))[1:]
        left_line = self.caster.level.get_points_in_line(lower_line[0], Level.Point(x, y))[1:]
        right_line = self.caster.level.get_points_in_line(lower_line[-1], Level.Point(x, y))[1:]
        return original_line+left_line+right_line

class SuperBlaster(Spells.OrbSpell):
    def on_init(self):
        self.name = "Super Blaster"
        self.range = 13
        self.max_charges = 1

        self.melt_walls = True

        self.minion_health = 30
        self.radius = 5
        self.damage = 60
        
        self.tags = [Level.Tags.Dark, Level.Tags.Orb, Level.Tags.Conjuration]
        self.level = 8

        self.upgrades['ultra_negative'] = (1, 6, "Beyond Darkness", "The orb can affect units that are immune to [dark] damage")
        self.upgrades['orb_eater'] = (1, 9, "Orb Eater", "The orb gains the on-move abilities of all of your other orbs.\nThis does not give the orb the spells or other abilities of your other orbs.")
        self.upgrades['death'] = (1, 5, "Pulsating Hate", "The orb deals a fixed 22 [dark] damage to all units in its pull radius plus one prior to pulling in units.")

    def get_description(self):
        return ("Launch an orb of raw negative energy.\n"
                "The orb melts through walls and sucks in enemies in a [{radius}_tiles:radius] each turn.\n"
                "Any enemy pulled adjacent to the orb with less than [{damage}_current_HP:dark] instantly dies if it is not immune to [dark].\n"
                "The orb can be destroyed by [dark] damage.").format(**self.fmt_dict())
        
    def on_make_orb(self, orb):
        orb.resists[Level.Tags.Dark] = 0
        orb.name = "Negative Energy Sphere"
        orb.tags = [Level.Tags.Dark]
        orb.recolor_primary = Level.Tags.Dark.color
        orb.recolor_secondary = Level.Tags.Dark.color
        orb.asset = ['FirstMod', 'toxic_orb']
                
    def on_orb_move(self, orb, next_point):
        if self.get_stat('death'):
           for point in [p for p in self.owner.level.get_points_in_ball(orb.x, orb.y, self.get_stat('radius')+1)]:
               if self.owner.x == point.x and self.owner.y == point.y:
                   continue
               self.owner.level.deal_damage(point.x, point.y, 22, Level.Tags.Dark, self)
        fly_triggered = False
        pull_points = [p for p in self.owner.level.get_points_in_ball(orb.x, orb.y, self.get_stat('radius'))]
        for p in pull_points:
            u = self.owner.level.get_unit_at(p.x, p.y)
            if not u or not Level.are_hostile(u, self.owner):
                continue
            if not u.flying:
                u.flying = fly_triggered = True
            if u and Level.are_hostile(u, self.owner):
                path = self.owner.level.get_points_in_line(u, Level.Point(orb.x, orb.y), find_clear=True, two_pass=True)[1:-1][:99]
                for p in path:
                    if self.owner.level.can_move(u, p.x, p.y, teleport=True):
                        self.owner.level.act_move(u, p.x, p.y, teleport=True)
                        self.owner.level.leap_effect(p.x, p.y, Level.Tags.Dark.color, u)
                    else:
                        break
                if Level.distance(u, orb) <= 1.5:
                    if u.cur_hp < self.get_stat('damage') and (u.resists[Level.Tags.Dark] < 100 and not self.get_stat('ultra_negative')):
                        u.kill()
            if fly_triggered:
                u.flying = False
        if self.get_stat('orb_eater'):
            all_onmoves = [i.on_orb_move for i in self.owner.spells if Spells.OrbSpell in type(i).__bases__ and type(i) != type(self)]
            for onmove in all_onmoves:
                onmove(orb, next_point)


class BloodOrbBuff(Level.Buff):
    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.spell = spell
        self.name = "Orb Passives"
        self.color = Level.Tags.Blood.color
        self.owner_triggers[Level.EventOnPreDamaged] = self.block

    def block(self, evt):
        if evt.damage <= math.ceil(self.owner.max_hp*0.13):
            self.owner.add_shields(1)
    
    def get_tooltip(self):
        return "Blocks all damage at or below 13% of its max HP."

class IronBlueBuff(Level.Buff):
    def __init__(self):
        self.first_spawn = True
        Level.Buff.__init__(self)
        self.name = "Iron-Blue Intention"
        self.color = Level.Tags.Ice.color
        self.owner_triggers[Level.EventOnDeath] = self.burst
        self.owner_triggers[Level.EventOnUnitAdded] = self.change_location

    def burst(self, evt):
        for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, 8):
            unit = self.owner.level.get_unit_at(*p)
            if unit and not Level.are_hostile(unit, self.owner):
                continue
            else:
                self.owner.level.deal_damage(p.x, p.y, 33, Level.Tags.Ice, self)
        self.first_spawn = False

    def change_location(self, evt):
        if not self.first_spawn and (b := self.owner.get_buff(Spells.OrbBuff)):
            valids = [p for p in self.owner.level.get_points_in_los(self.owner) if Level.distance(self.owner, p) >= 5]
            if not valids:
                self.owner.kill()
            else:
                b.dest = random.choice(valids)
                self.owner.turns_left = len(self.owner.level.get_points_in_line(self.owner, b.dest))
    
    def get_tooltip(self):
        return "Deals a fixed 33 ice damage to enemies in an 8-tile radius on death. Will automatically target a new tile when reincarnating."


class VampireOrb(Spells.OrbSpell):
    def on_init(self):
        self.name = "Blood Orb"
        self.range = 9
        self.max_charges = 2

        self.minion_health = 65
        ex = Monsters.Vampire()
        self.minion_damage = ex.spells[0].damage
        
        self.tags = [Level.Tags.Dark, Level.Tags.Orb, Level.Tags.Conjuration, Level.Tags.Blood]
        self.level = 6

        self.hp_cost = 13

        self.upgrades['variants'] = (1, 6, "Monster Dance", "Vampires randomly gain either [clay:physical], [chaos], or [metallic].")
        self.upgrades['ghosts'] = (1, 5, "Bloody Tears", "The orb also summons 2 bloodghasts each turn, which inherit one quarter of this spell's HP bonuses.")
        self.upgrades['demonize'] = (1, 4, "Demon Seed", "Vampires gain [demon] and [nature] until killed.")
        self.upgrades['respawn'] = (1, 6, "Iron-Blue Intention", "The orb also emits a burst of ice when it expires or is killed, dealing a fixed 33 [ice] damage to enemies in a [8-tile_radius:radius].\nIf the orb reincarnates, it will automatically retarget to a new point at least 5 tiles away from itself.\nThe orb will instantly die if it cannot.")

    def sourceify(self, unit):
        mhp = unit.max_hp
        unit.source = self
        CommonContent.apply_minion_bonuses(self, unit)
        div = 4 if "bloodghast" in unit.name else 2
        unit.max_hp = mhp + (self.get_stat('minion_health')-self.minion_health)//div
        return unit
    
    def get_extra_examine_tooltips(self):
        return [self.sourceify(Monsters.Vampire())] + self.spell_upgrades[:2] + [self.sourceify(Monsters.Bloodghast())] + self.spell_upgrades[2:]

    def get_description(self):
        return ("Launch an orb of blood, which moves one tile towards the target each turn.\n"
                "The orb summons a vampire next to itself each turn, which inherits one half of this spell's HP bonuses.\n"
                "Unlike most orbs, the orb has low resistances and instead blocks all damage at or below [13%_of_its_max_HP:dark].\n"
                "The blocking effect counts damage before resistances.").format(**self.fmt_dict())
        
    def on_make_orb(self, orb):
        orb.resists[Level.Tags.Dark] = 0
        orb.resists[Level.Tags.Fire] = 0
        orb.resists[Level.Tags.Ice] = 0
        orb.resists[Level.Tags.Lightning] = 0
        orb.resists[Level.Tags.Holy] = 0
        orb.resists[Level.Tags.Physical] = 0
        orb.resists[Level.Tags.Arcane] = 0
        orb.name = "Orb of Blood"
        orb.tags = [Level.Tags.Blood]
        orb.asset = ['FirstMod', 'blood_orb']
        orb.buffs.append(BloodOrbBuff(self))
        if self.get_stat('respawn'):
            orb.apply_buff(IronBlueBuff())
                
    def on_orb_move(self, orb, next_point):
        vamp = self.sourceify(Monsters.Vampire())
        if self.get_stat('demonize'):
            vamp.tags.extend([Level.Tags.Nature, Level.Tags.Demon])
        if self.get_stat('variants'):
            BossSpawns.apply_modifier(random.choice([BossSpawns.Chaostouched, BossSpawns.Claytouched, BossSpawns.Metallic]), vamp)
        self.summon(vamp, target=orb, radius=5)
        if self.get_stat('ghosts'):
            for _ in range(2):
                self.summon(self.sourceify(Monsters.Bloodghast()), target=orb, radius=5)

class WhaleFormBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.transform_asset_name = "3x3_spider_queen"
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.stack_type = Level.STACK_TYPE_TRANSFORM
        self.had_flying = self.had_burrowing = 0
        self.color = Level.Tags.Nature.color
        self.name = "Cetacean Form"
        self.owner_triggers[Level.EventOnMoved] = self.proc_spell
        self.resists[Level.Tags.Physical] = 75
        if self.spell.get_stat('force'):
            self.tag_bonuses[Level.Tags.Nature]["radius"] = 2
            self.tag_bonuses[Level.Tags.Nature]["minion_health"] = 15
        if self.spell.get_stat('hero'):
            self.tag_bonuses[Level.Tags.Holy]['max_charges'] = 1
        self.can_casts = {}
        self.invinc = RareMonsters.IdolOfShieldingSpell()
    
    def on_applied(self, owner):
        self.owner.radius = 1
        self.owner.had_flying = self.owner.flying
        self.owner.had_burrowing = self.owner.burrowing
        self.owner.flying = True
        self.owner.burrowing = True
        self.owner.max_hp += 150
        self.owner.cur_hp = self.owner.max_hp
        if self.spell.get_stat('champion'):
            self.invinc.owner = self.invinc.caster = self.owner
            self.invinc.max_charges = 2
            self.invinc.cur_charges = self.invinc.get_stat('max_charges')
            self.invinc.cool_down = 0
            self.invinc.tags.append(Level.Tags.Nature)
            self.owner.spells.append(self.invinc)

    def on_unapplied(self):
        self.owner.radius = 0
        self.owner.flying = self.owner.had_flying
        self.owner.burrowing = self.owner.had_burrowing
        self.owner.max_hp = max(1,self.owner.max_hp - 150)
        self.owner.cur_hp = min(self.owner.cur_hp, self.owner.max_hp)
        self.owner.remove_spell(self.invinc)
    
    def proc_spell(self, evt):
        if not evt.teleport:
            self.owner.level.act_cast(self.owner, self.owner.get_or_make_spell(Spells.EarthquakeSpell), self.owner.x, self.owner.y, False)
    
    def modify_spell(self, spell):
        if not (Level.Tags.Nature in spell.tags or (Level.Tags.Holy in spell.tags and self.spell.get_stat('hero'))):
            def cannot_cast(*args, **kwargs):
                return False

            self.can_casts[spell] = spell.can_cast
            spell.can_cast = cannot_cast

    def unmodify_spell(self, spell):
        if spell in self.can_casts:
            spell.can_cast = self.can_casts[spell]

class WhaleForm(Spells.Spell):
    def on_init(self):
        self.name = "Cetacean Form"
        self.range = 0
        self.max_charges = 2
        self.duration = 14
        self.level = 7
        
        self.tags = [Level.Tags.Nature, Level.Tags.Enchantment, Level.Tags.Holy]

        self.upgrades['force'] = (1, 4, "Natural Force", "[Nature:nature] spells and skills gain 2 radius and 15 minion health while in whale form.")
        self.upgrades['champion'] = (1, 6, "Defender of the Depths", "You gain the Idol of Invincibility spell while in whale form. It starts with two charges and is considered a [nature] spell, gaining any appropriate bonuses.")
        self.upgrades['hero'] = (1, 6, "Sealight", "[Holy] spells gain 1 max charge and can be cast in whale form.")

    def can_cast(self, x, y):
        adjacents = [p for p in self.caster.level.get_adjacent_points(Level.Point(x, y), False, False)]
        return all(not self.owner.level.tiles[p.x][p.y].is_wall() and not self.caster.level.get_unit_at(p.x, p.y) for p in adjacents)

    def get_description(self):
        return ("Transform into a legendary whale for [{duration}_turns:duration].\n"
                "You become a 3x3 unit, and gain flying and burrowing. You also gain 150 max HP and 75 [physical] resist.\n"
                "Whenever you move without teleporting, cast your Earthquake spell.\n"
                "You can only cast [nature] spells while in whale form."
                ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        self.owner.apply_buff(WhaleFormBuff(self), self.get_stat('duration'))

class PylonPower(Level.Buff):

    def __init__(self, spell):
        self.turn_count = 0
        self.radius = 5
        self.spell = spell
        Level.Buff.__init__(self)
        self.color = Level.Tags.Dark.color
        self.name = "Power Construct"

    def on_advance(self):
        points = [p for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.radius)]
        for p in random.sample(points, 7):
            self.owner.level.deal_damage(p.x, p.y, 0, Level.Tags.Arcane, self)
        for p in points:
            if (u := self.owner.level.get_unit_at(p.x, p.y)):
                buff = Level.Buff()
                buff.global_bonuses["damage"] = self.spell.get_stat('bonus')
                buff.stack_type = Level.STACK_NONE
                buff.name = "Pylon Power"
                buff.color = Level.Tags.Arcane.color
                u.apply_buff(buff, 1)

    def get_tooltip(self):
        return "Grants all units in a %d tile radius a bonus to damage." % self.radius


class FrostMan(Level.Spell):

    def on_init(self):
        self.name = "Frost Wave"
        self.range = 50
        self.requires_los = False
        self.damage = 17
        self.max_charges = 3
        self.tags = [Level.Tags.Ice, Level.Tags.Sorcery]
        self.duration = 4

        self.level = 4

        self.upgrades['steam'] = (1, 4, "Freezer Burn", "All units hit by the wave take a fixed 1 [fire] damage after the wave attempts to freeze them.")
        self.upgrades['blade'] = (1, 5, "Blade Wave", "The wave deals [physical] damage to each target before freezing, mulitplied by 1 plus the absolute value of its [ice] resist percentage.")
        self.add_upgrade(LastBasedHaste())

    def get_description(self):
        return (
            "A wave of frost follows a path to the target point, dealing [{damage}_ice_damage:damage] to everything in its path.\n"
            "Any units caught in the wave are frozen for [{duration}_turns:duration].\n"
            "The wave will not move over chasms and cannot target walls or chasms."
        ).format(**self.fmt_dict())

    def can_cast(self, x, y):
        if self.owner.level.tiles[x][y].is_wall() or self.owner.level.tiles[x][y].is_chasm:
            return False
        path = self.get_impacted_tiles(x, y)
        return len(path) > 0 and Level.Spell.can_cast(self, x, y)
    
    def get_impacted_tiles(self, x, y):
        pather = Level.Unit()
        path = self.owner.level.find_path(self.owner, Level.Point(x, y), pather, pythonize=True, unit_penalty=0)
        return path

    def cast(self, x, y, channel_cast=False):
        path = self.get_impacted_tiles(x, y)
        for p in path:
            self.owner.level.deal_damage(p.x, p.y, self.get_stat('damage'), Level.Tags.Ice, self)
            if (u := self.owner.level.get_unit_at(x, y)):
                if self.get_stat('blade'):
                    mult = 1 + abs(u.resists[Level.Tags.Ice]//100)
                    u.deal_damage(math.floor(mult*self.get_stat('damage')), Level.Tags.Physical, self)
                u.apply_buff(CommonContent.FrozenBuff(), self.get_stat('duration'))
                if self.get_stat('steam'):
                    u.deal_damage(1, Level.Tags.Fire, self)
            yield

class TempHaste(Level.Buff):
    def __init__(self, sp):
        Level.Buff.__init__(self)
        self.name = "%s Haste" % sp().name
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.color = Level.Tags.Holy.color
        self.spell_bonuses[sp]['quick_cast'] = 1
        self.global_triggers[Level.EventOnSpellCast] = self.dispel
        self.remove = False
    
    def dispel(self, evt):
        if self.remove:
            self.owner.remove_buff(self)
        if type(evt.spell) == FrostMan:
            self.remove = True
            
class LastBasedHaste(Upgrades.Upgrade):
    def on_init(self):
        self.prereq = FrostMan
        self.name = "Pure Snow"
        self.level = 4
        self.description = "Frost Wave can be cast instantly if a [holy] spell was cast before it that consumed a turn."
        self.owner_triggers[Level.EventOnSpellCast] = self.update

    def update(self, evt):
        if Level.Tags.Holy in evt.spell.tags and not evt.spell.quick_cast:
            self.owner.apply_buff(TempHaste(type(self.prereq)))

#asset hack because dylan wont let me be lazy
def monkey_asset(spellcls):
    spell = spellcls()
    if not spell.asset:
        spell.asset = ["FirstMod", "mammoth"]
    return lambda: spell

#Spells.all_player_spell_constructors.clear()

Spells.all_player_spell_constructors.extend([monkey_asset(i) for i in [SiegeEngine, BigSpell, MinionLichForm, Hoops, FlyTrap, Taunt, Krabby, TheHarvest, BeegJar, BloodDrive, InsectRush, LionCall, MedusaForm, ShamanCall, TwilightSeer, TestingVariant, MultiMove, RainbowGrenade, Snowblind, WeirdFurnace, DarkSlime, CallAncient, LightSlime, BloodySlime, MageMoves, GiantAxe, SwordCurse, RealCoven, Warlock, RAGING, MoonCrash, Pachy, VenomSentinel, Formchanger, ChaosPlants, PonderTheOrb, WormBurrow, PoisonDragon, SaltEffigy, ChaosBurn, Boney, BizarreOath, GoldSpider, GCFW, RitualOfLife, PortalBuster, Dishwasher, CrystalMode, IceShiv, BloodElectro, FaePact, WallToss, Clayize, ApepPop, Predestine, SlowTax, MindTax, RazorScales, StormRecycle, SphinxSpell, FunnyBombSpell, RayPierceSpell, MagicMinigun, SuperBlaster, VampireOrb, WhaleForm]])
#Spells.all_player_spell_constructors.append(Dummy)
#Spells.all_player_spell_constructors.append(DummyBone)
#Spells.all_player_spell_constructors.append(TrueSlime)
#Spells.all_player_spell_constructors.extend([TensionTest, TensionDance])
Spells.all_player_spell_constructors.extend([monkey_asset(i) for i in [MagmaSword, WHALE, Sponge, MeltCreep, FrostMan]]) #mega man x reference spells
#new enemies

class CurseXVI(Level.Spell):
    def on_init(self):
        self.name = "Curse XVI"
        self.range = 0
        self.cool_down = 17
    
    def get_ai_target(self):
        return self.caster

    def get_description(self):
        return "All enemy units deal 50% reduced spell damage for 4 turns"

    def cast_instant(self, x, y):
        for e in [u for u in self.caster.level.units if Level.are_hostile(self.caster, u)]:
            debuff = Level.Buff()
            debuff.name = "Curse"
            debuff.buff_type = Level.BUFF_TYPE_CURSE
            debuff.color = Level.Tags.Arcane.color
            debuff.global_bonuses_pct["damage"] = -50
            e.apply_buff(debuff, 4)

class SlowBuff(Level.Buff):
    def __init__(self, magnitude):
        self.magnitude = magnitude
        Level.Buff.__init__(self)
        self.name = "Slow"
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.color = Level.Tags.Ice.color
        self.affected = []

    def modify_spell(self, spell):
        if spell.cool_down >= 0:
            spell.cool_down += self.magnitude

    def unmodify_spell(self, spell):
        if spell in self.affected:
            spell.cool_down -= self.magnitude

class SlowXVI(Level.Spell):
    def on_init(self):
        self.name = "Slow XVI"
        self.range = 0
        self.cool_down = 44
    
    def get_ai_target(self):
        return self.caster

    def get_description(self):
        return "All enemy spells gain 8 cooldown for 24 turns"

    def cast_instant(self, x, y):
        for e in [u for u in self.caster.level.units if Level.are_hostile(self.caster, u)]:
            e.apply_buff(SlowBuff(8), 24)

class DispelXVI(Level.Spell):
    def on_init(self):
        self.name = "Dispel XVI"
        self.range = 0
        self.cool_down = 25
    
    def get_ai_target(self):
        return self.caster

    def get_description(self):
        return "Remove all buffs from all enemies"

    def cast_instant(self, x, y):
        for e in [u for u in self.caster.level.units if Level.are_hostile(self.caster, u)]:
            buffs = [b for b in e.buffs if b.buff_type == Level.BUFF_TYPE_BLESS]
            if not buffs:
                return
            for b in buffs:
                e.remove_buff(b)


def Mateus():
    emp = Level.Unit()
    emp.max_hp = 1666
    emp.tags = [Level.Tags.Dark, Level.Tags.Demon]
    emp.resists[Level.Tags.Dark] = 100
    emp.resists[Level.Tags.Holy] = -50
    emp.shields = 1
    emp.name = "Mateus, Emperor of Hell"
    emp.asset_name = os.path.join("..","..","mods","FirstMod","crab_abominable")
    meteo = Spells.MeteorShower()
    meteo.name = "Starfall X"
    meteo.max_charges = 0
    meteo.num_targets *= 2
    meteo.cool_down = 20
    melee = CommonContent.SimpleMeleeAttack(damage=14, damage_type=Level.Tags.Dark, attacks=8, drain=True)
    emp.spells.extend([SlowXVI(), meteo, DispelXVI(), CurseXVI(), melee])
    return emp

def Secret():
    emp = Level.Unit()
    emp.max_hp = 120
    emp.shields = 2
    emp.name = "Dylan, the First Wizard"
    emp.asset_name = "player_phantom"
    emp.tags = [Level.Tags.Living]
    emp.buffs.append(CommonContent.ReincarnationBuff(10))
    idol_func = lambda: random.choice([lambda : RareMonsters.DampenerIdol('Weak', 'damage', 4), lambda: RareMonsters.DampenerIdol('Foolish', 'range', 1), lambda: RareMonsters.DampenerIdol('Fickle', 'duration', 3)])()
    idol_func2 = lambda: random.choice([RareMonsters.ConcussiveIdol, RareMonsters.CrucibleOfPain, RareMonsters.IdolOfFieryVengeance, RareMonsters.IdolOfSlime])()
    pantheism = CommonContent.SimpleSummon(spawn_func=idol_func, num_summons=3, cool_down=15, global_summon=True)
    pantheism.name = "Pantheism"
    pantheism.description = "Summons 3 Idols of the Weak, Foolish, or Fickle randomly."
    theocracy = CommonContent.SimpleSummon(spawn_func=idol_func2, num_summons=3, cool_down=25, global_summon=True)
    theocracy.name = "Theocracy"
    theocracy.description = "Summons 3 Concussive Idols, Crucibles of Pain, Slimesoul Idols, or Idols of Fiery Vengeance randomly."
    hounding = CommonContent.SimpleSummon(spawn_func=Variants.ChaosHound, num_summons=4, cool_down=9, max_channel=3)
    hounding.name = "Entropic Birth"
    def hallate_onhit(c, t):
        if t.is_player_controlled:
            for s in t.spells:
                t.cool_downs[s] = t.cool_downs.get(s, 0) + 2
        elif Level.are_hostile(c, t):
            for s in t.spells:
                t.cool_downs[s] = t.cool_downs.get(s, 0) + 4
    hallation = CommonContent.SimpleBurst(damage=12, radius=6, damage_type=Level.Tags.Holy, cool_down=5, onhit=hallate_onhit)
    hallation.name = "Hallation"
    hallation.description = "Hit units gain +4 cooldown to all spells. If the Wizard is hit, they get +2 cooldown instead."
    emp.spells = [theocracy, pantheism, hounding, hallation, CommonContent.SimpleMeleeAttack(100)]
    return emp

#Monsters.spawn_options.append((Mateus, 1))  
#Monsters.spawn_options.append((Secret, 1)) 

#new equips

class GenericLvSummonStaff(Equipment.Equipment):
    def __init__(self, name, tag, table, near_target=False):
        
        self.tag = tag
        self.table = table
        Equipment.Equipment.__init__(self)
        self.name = name
        self.near_target = near_target

        self.owner_triggers[Level.EventOnSpellCast] = self.cast
        self.slot = Level.ITEM_SLOT_STAFF
        desc = ""

        for k in self.table.keys():
            if isinstance(k, tuple):
                base = "Whenever you cast a level "
                k_conv = [str(i) for i in k]
                k_neo = ["%s, " % i for i in k_conv[:-1]] + ['or %s' % k_conv[-1]]
                base += ''.join(k_neo)
                base += " [%s] spell, summon a%s %s%s.\n" % (self.tag.name.lower(), ("n" if self.table[k]().name.lower()[0] in ["a", "e", "i", "o", "u"] else ""), self.table[k]().name.lower(), (" near the target" if self.near_target else ""))
            else:
                base = "Whenever you cast a level %d [%s] spell, summon a%s %s%s.\n" % (k, self.tag.name.lower(), ("n" if self.table[k]().name.lower()[0] in ["a", "e", "i", "o", "u"] else ""), self.table[k]().name.lower(), (" near the target" if self.near_target else ""))
            desc += base
        desc.rstrip()
        self.description = desc

    def cast(self, evt):
        if self.tag not in evt.spell.tags:
            return
        else:
            for k in self.table.keys():
                if evt.spell.level == k:
                    self.do_summon(evt.x, evt.y, k)
                elif isinstance(k, tuple) and evt.spell.level in k:
                    self.do_summon(evt.x, evt.y, k)
    
    def do_summon(self, x, y, key):
        mon = self.table[key]()
        CommonContent.apply_minion_bonuses(self, mon)
        if not self.near_target:
            self.summon(mon)
        else:
            self.summon(mon, Level.Point(x, y))

class MinionBuffStaff(Equipment.Equipment):
    def __init__(self, name, buffclass, tag_whitelist=[], buff_duration=0):
        
        Equipment.Equipment.__init__(self)
        self.name = name
        self.buffclass = buffclass
        self.tag_whitelist = tag_whitelist
        self.buff_duration = buff_duration

        self.global_triggers[Level.EventOnUnitAdded] = self.apply_minion_buff
        self.slot = Level.ITEM_SLOT_STAFF
        desc = "Minions you summon"
        if tag_whitelist:
            tnames = [t.name for t in tag_whitelist]
            tailconv = ["[%s]" % s.lower() for s in tnames[-2:]]
            headconv = ["[%s]" % s.lower() for s in tnames[:-2]]
            clause = ", ".join(headconv + [" or ".join(tailconv)])
            desc = clause + " " + desc.lower()
        desc += " gain %s" % self.buffclass().name
        if buff_duration:
            desc += " for %d turns" % buff_duration
        desc += " when summoned."
        if tag_whitelist:
            desc = desc[:1] + desc[1].upper() + desc[2:]
        desc.rstrip()
        self.description = desc

    def apply_minion_buff(self, evt):
        if Level.are_hostile(evt.unit, self.owner):
            return
        elif self.tag_whitelist and not any(t in self.tag_whitelist for t in evt.unit.tags):
            return
        evt.unit.apply_buff(self.buffclass(), self.buff_duration)

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

class JankGodRobe(Equipment.Equipment):

    def on_init(self):
        self.slot = Level.ITEM_SLOT_ROBE
        self.name = "Johnsbane"
        self.description = "All skill effects are doubled."
        self.owner_triggers[Level.EventOnBuffApply] = self.check

    def clone(self, buff):
        if Upgrades.Upgrade in type(buff).__bases__ and " Clone" not in buff.name:
            clone = type(buff)()
            clone.name = buff.name + " Clone"
            self.owner.apply_buff(clone)

    def on_applied(self, owner):
        for b in owner.buffs:
            self.clone(b)
    
    def check(self, evt):
        self.clone(evt.buff)

    def on_unapplied(self):
        for b in self.owner.buffs:
            if " Clone" in b.name:
                self.owner.remove_buff(b)  

class ZomaHelmet(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_HEAD
        self.name = "Zoma's Helmet"
        self.description = "Your summoned [undead] allies gain [demon] and vice versa."
        self.global_triggers[Level.EventOnUnitAdded] = self.check
        self.resists[Level.Tags.Holy] = -100

    def check(self, evt):
        if Level.are_hostile(evt.unit, self.owner):
            return
        elif Level.Tags.Demon in evt.unit.tags and Level.Tags.Undead not in evt.unit.tags:
            evt.unit.tags.append(Level.Tags.Undead)
        elif Level.Tags.Undead in evt.unit.tags and Level.Tags.Demon not in evt.unit.tags:
            evt.unit.tags.append(Level.Tags.Demon)

class DestroyerStaff(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_STAFF
        self.name = "Staff of Destruction"
        self.description = "You have a 1/3 chance to be stunned for 1 turn each turn."
        self.global_bonuses_pct["damage"] = 75

    def on_advance(self):
        if random.random() < .33:
            self.owner.apply_buff(Level.Stun(), 1)

class HircineRobe(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_ROBE
        self.name = "Savior's Hide"
        self.description = "Take 1 damage of the type you are least resistant to each turn, choosing randomly if there is a tie."
        for t in [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Holy, Level.Tags.Dark, Level.Tags.Arcane, Level.Tags.Poison, Level.Tags.Physical]:
            self.resists[t] = 25

    def on_advance(self):
        mins = {key:val for key,val in self.owner.resists.items() if val == min(self.owner.resists.values())}
        valids = list(mins.keys())
        if not valids:
            return
        self.owner.deal_damage(1, random.choice(valids), self)

class RedJacket(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_ROBE
        self.name = "Red Jacket"
        self.description = "Whenever you witness an enemy take [fire] damage, you heal for a quarter of that amount."
        self.resists[Level.Tags.Fire] = 100
        self.global_triggers[Level.EventOnDamaged] = self.on_spell_cast

    def on_spell_cast(self, event):
        if event.damage_type != Level.Tags.Fire:
            return

        heal = event.damage // 4
        if heal <= 0:
            return

        if not Level.are_hostile(self.owner, event.unit):
            return

        if self.owner in self.owner.level.get_units_in_los(event.unit):
            self.owner.deal_damage(-heal, Level.Tags.Heal, self)

class RubyCharm(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_AMULET
        self.name = "Ruby Charm"
        self.description = "Will be consumed to grant 1 SH before a fatal blow."
        self.owner_triggers[Level.EventOnPreDamaged] = self.lifeward

    def lifeward(self, evt):
        multiplier = (100 - evt.unit.resists[evt.damage_type]) / 100.0
        if(evt.damage*multiplier) >= self.owner.cur_hp:
            self.owner.add_shields(1)
        self.owner.remove_buff(self)

class GiantWrench(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_STAFF
        self.name = "Giant Wrench"
        self.tag_bonuses[Level.Tags.Metallic]["duration"] = 5
        self.tag_bonuses[Level.Tags.Metallic]["minion_health"] = 15
        self.tag_bonuses[Level.Tags.Metallic]["max_charges"] = 2

class Taxes(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_AMULET
        self.name = "Tax Man's Tools"
        self.description = "Whenever an ally is healed, that ally will be healed again for one-quarter the original amount if the source of healing dealt damage in the same turn."
        self.global_triggers[Level.EventOnDamaged] = self.check
        self.global_triggers[Level.EventOnHealed] = self.boost
        self.damage_sources = []

    def on_pre_advance(self):
        self.damage_sources.clear()

    def check(self, evt):
        if evt.damage > 0 and evt.damage_type != Level.Tags.Heal:
            self.damage_sources.append(evt.source)

    def boost(self, evt):            
        if evt.heal <= -1 and evt.source in self.damage_sources and not Level.are_hostile(evt.unit, self.owner):
            heal = evt.heal // 4
            if heal > -1:
                return
            evt.unit.deal_damage(heal, Level.Tags.Heal, self)

class Phial(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_AMULET
        self.name = "Elemental Phial"
        self.description = "Temporary [elemental] allies last 10 turns longer."
        self.global_triggers[Level.EventOnUnitAdded] = self.modify

    def modify(self, evt):
        if Level.Tags.Elemental in evt.unit.tags and evt.unit.turns_to_death != None and not Level.are_hostile(self.owner, evt.unit):
            evt.unit.turns_to_death += 10

class BlindedByTheLight(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_STAFF
        self.name = "Dazzling Lightrod"
        self.description = "You have a 50% chance to be [blinded:blind] for 1 turn each turn, but all allies gain [holy]."
        self.global_triggers[Level.EventOnUnitPreAdded] = self.modify

    def modify(self, evt):
        if not Level.are_hostile(self.owner, evt.unit) and Level.Tags.Holy not in evt.unit.tags:
            evt.unit.tags.append(Level.Tags.Holy)

    def on_advance(self):
        if random.random() < .5:
            self.owner.apply_buff(Level.BlindBuff(), 1)

class Overdrive(Equipment.Equipment):
    def on_init(self):
        self.slot = Level.ITEM_SLOT_STAFF
        self.name = "Overclocker"
        self.description = "[Metallic] allies you summon become [electric:lightning] variants with the same HP."
        self.global_triggers[Level.EventOnUnitPreAdded] = self.modify

    def modify(self, evt):
        if not Level.are_hostile(self.owner, evt.unit) and Level.Tags.Metallic in evt.unit.tags:
            BossSpawns.apply_modifier(BossSpawns.Stormtouched, evt.unit)

class StaticShoes(Equipment.Equipment):
    
    def on_init(self):
        self.name = "Static Shockers"
        self.slot = Level.ITEM_SLOT_BOOTS
        self.description = "When hit, deal 4 [lightning] damage to the attacker for every step you have taken since the last time you activated this effect."
        self.charges = 0
        self.owner_triggers[Level.EventOnMoved] = self.on_move
        self.owner_triggers[Level.EventOnDamaged] = self.discharge

    def on_move(self, evt):
        if evt.teleport:
            return
        self.charges += 1

    def discharge(self, evt):
        if type(evt.source) == Level.Unit:
            victim = evt.source
        else:
            victim = evt.source.owner
        victim.deal_damage(4*self.charges, Level.Tags.Lightning, self)
        self.charges = 0

class CeleritousOld(Equipment.Equipment):
    
    def on_init(self):
        self.name = "Celeritous Cloak"
        self.slot = Level.ITEM_SLOT_BOOTS
        self.description = "The first spell you cast each realm does not use a turn. -4 to all ability cooldowns if equipped by someone other than the Wizard."
        self.owner_triggers[Level.EventOnSpellCast] = self.log
        self.owner_triggers[Level.EventOnUnitAdded] = self.reset
        self.last_cast = None
        self.cooldowns_old = {}

    def modify_spell(self, spell):
        if self.owner.is_player_controlled:
            spell.quick_cast = True
        else:
            self.cooldowns_old[spell] = self.owner.cool_downs[spell]
            self.owner.cool_downs[spell] = max(0, self.owner.cool_downs[spell]-4)
            
    def unmodify_spell(self, spell):
        if self.owner.is_player_controlled:
            spell.quick_cast = False
        else:
            self.owner.cool_downs[spell] = self.cooldowns_old[spell]

    def log(self, evt):
        if self.owner.is_player_controlled:
            self.last_cast = evt.spell

    def on_advance(self):
        if self.last_cast:
            for s in self.owner.spells:
                self.unmodify_spell(s)

    def reset(self, evt):
        for s in self.owner.spells:
            self.modify_spell(s)
        self.last_cast = None

class Celeritous(Equipment.Equipment):
    
    def on_init(self):
        self.name = "Celeritous Cloak"
        self.slot = Level.ITEM_SLOT_ROBE
        self.description = "The first spell you cast each realm does not use a turn. -4 to all ability cooldowns if equipped by someone other than the Wizard."
        self.owner_triggers[Level.EventOnSpellCast] = self.log
        self.owner_triggers[Level.EventOnUnitAdded] = self.reset
        self.quickcasts = 0
        self.cooldowns_old = {}

    def modify_spell(self, spell):
        if self.owner.is_player_controlled:
            spell.quick_cast = True
        else:
            self.cooldowns_old[spell] = spell.cool_down
            spell.cool_down = max(0, spell.cool_down-4)
            
    def unmodify_spell(self, spell):
        if self.owner.is_player_controlled:
            spell.quick_cast = False
        else:
            spell.cool_down = self.cooldowns_old[spell]

    def log(self, evt):
        if self.owner.is_player_controlled:
            self.quickcasts += 1
            if self.quickcasts > 1:
                for s in self.owner.spells:
                    self.unmodify_spell(s)

    def reset(self, evt):
        self.quickcasts = 0

class AcidRobe(Equipment.Equipment):
    
    def on_init(self):
        self.name = "Living Acid Robe"
        self.slot = Level.ITEM_SLOT_ROBE
        self.description = "Enemy attackers take [poison] damage equal to a quarter of the damage they deal."
        self.owner_triggers[Level.EventOnDamaged] = self.retaliate
        self.resists[Level.Tags.Poison] = -100

    def retaliate(self, evt):
        if type(evt.source) == Level.Unit:
            victim = evt.source
        else:
            victim = evt.source.owner
        if not Level.are_hostile(victim, self.owner):
            return
        dmg = evt.damage // 4
        if dmg <= 0:
            return
        victim.deal_damage(dmg, Level.Tags.Poison, self)

class Herdstaff(Equipment.Equipment):
    
    def on_init(self):
        self.name = "Opportunist's Herding Staff"
        self.slot = Level.ITEM_SLOT_STAFF
        self.description = "Exotic pets and sigils you own are treated as if summoned by a [nature] [conjuration] spell."
        self.global_triggers[Level.EventOnUnitPreAdded] = self.modify_pet

    def modify_pet(self, evt):
        if Level.are_hostile(evt.unit, self.owner) or type(evt.unit.source) not in [Equipment.PetCollar, Equipment.PetSigil]:
            return
        dummy = Level.Spell()
        dummy.tags = [Level.Tags.Nature, Level.Tags.Conjuration]
        dummy.minion_health = evt.unit.max_hp
        dummy.minion_damage = max([getattr(s, "damage", 0) for s in evt.unit.spells])
        dummy.minion_range = max([getattr(s, "range", 0) for s in evt.unit.spells])
        dummy.statholder = self.owner
        CommonContent.apply_minion_bonuses(dummy, evt.unit)


#Equipment.all_items.append(JankGodRobe)
#Equipment.all_items.append(ZomaHelmet)
#Equipment.all_items.append(DestroyerStaff)
#Equipment.all_items.append(HircineRobe)
#Equipment.all_items.append(RedJacket)
#Equipment.all_items.append(RubyCharm)
#Equipment.all_items.append(GiantWrench)
#Equipment.all_items.append(Taxes)
#Equipment.all_items.append(Phial)
#Equipment.all_items.append(BlindedByTheLight)
#Equipment.all_items.append(Overdrive)
#Equipment.all_items.append(StaticShoes)
#Equipment.all_items.append(Celeritous)
#Equipment.all_items.append(AcidRobe)
#Equipment.all_items.append(Herdstaff)

#Equipment.all_items.append(lambda: MinionBuffStaff("Crimson Crook", lambda: CommonContent.BloodrageBuff(3), tag_whitelist=[Level.Tags.Demon, Level.Tags.Blood], buff_duration=10))
#Equipment.all_items.append(lambda: MinionBuffStaff("Oar of Charon", lambda: CommonContent.ReincarnationBuff(1), tag_whitelist=[Level.Tags.Undead], buff_duration=6))
#Equipment.all_items.append(lambda: MinionBuffStaff("Time Staff", lambda: GenericHasteBuff(2), buff_duration=4))

#Equipment.all_items.append(Equipment.BootsOfDramaticArrival)