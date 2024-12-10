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
import text


class DustCloud(Level.Cloud):

    def __init__(self, owner, spell):
        Level.Cloud.__init__(self)
        self.owner = owner
        self.duration = spell.get_stat('duration')
        self.name = "Dust Cloud"
        self.source = spell
        self.asset = ["ATGMPack", "other_assets", "dust_cloud"]
        self.spell = spell

    def get_description(self):
        basic = "Each turn, deals %d physical damage to units inside." % self.spell.get_stat('damage')
        if self.spell.get_stat('eternity') and self.duration <= 0:
            persist_chance = (1 + self.duration*0.01)
            new = "\nHas a %d%% chance to stay alive next turn." % (persist_chance*100)  
        else:
            new = "\nExpires in %d turns." % self.duration
        return basic + new

    def on_advance(self):
        u = self.owner.level.get_unit_at(self.x, self.y)
        if u:
            u.deal_damage(self.spell.get_stat('damage'), Level.Tags.Physical, self.spell)
            if self.spell.get_stat('ash'):
                u.deal_damage(7, random.choice([Level.Tags.Fire, Level.Tags.Dark, Level.Tags.Poison]), self.spell)
                u.apply_buff(Level.BlindBuff(), 1)
            if self.spell.get_stat('papercut'):
                for _ in range(self.spell.get_stat('damage')):
                    u.deal_damage(1, Level.Tags.Physical, self.spell)
    
    def advance(self):
        self.duration -= 1
        self.on_advance()
        if self.duration <= 0 and self.is_alive:
            if self.spell.get_stat('eternity'):
                persist_chance = (1 + self.duration*0.01)
                c = random.random()
                if c > persist_chance:
                    self.kill()
            else:
                self.kill()
        return True


class DustBowl(Level.Spell):
    def on_init(self):
        self.name = "Dust Bowl"
        self.max_charges = 5
        self.level = 4
        self.tags = [Level.Tags.Metallic, Level.Tags.Enchantment, Level.Tags.Nature ]
        self.range = 9
        self.damage = 6
        self.duration = 13
        self.requires_los = False

        self.asset = ["ATGMPack", "icons", "dustbowl"]

        self.upgrades['ash'] = (1, 4, "Ash Bowl", "Dust clouds also deal 7 [fire], [dark], or [poison] damage randomly and [blind:holy] units inside for 1 turn.")
        self.upgrades['papercut'] = (1, 3, "Paper Dust", "Dust clouds deal a number of additional hits of 1 [physical] damage equal to this spell's damage.")
        self.upgrades['eternity'] = (1, 5, "Bowl of the Millennium", "Clouds have a chance to stay alive each turn past their usual duration.\nThis chance starts at 100% and decreases by 1% each turn the cloud exists past this spell's duration stat.")
        

    def get_impacted_tiles(self, x, y):
        angle = math.pi / 6
        target = Level.Point(x, y)
        burst = Level.Burst(self.caster.level, self.caster, self.get_stat('range'), burst_cone_params=Level.BurstConeParams(target, angle), expand_diagonals=True)
        return [p for stage in burst for p in stage]
    
    def get_description(self):
        return (
            "Throws a cloud of metallic dust on each tile in a cone.\n"
            "Dust clouds deal [{damage}_damage:damage] [physical:physical] damage to enemies standing in them.\n"
            "The clouds last [{duration}_turns:duration]."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        for t in self.get_impacted_tiles(x, y):
            self.caster.level.add_obj(DustCloud(self.caster, self), t.x, t.y)

class Slimeteor(Level.Spell):
    def on_init(self):
        self.name = "Slimeteor"
        self.max_charges = 3
        self.level = 5
        self.tags = [Level.Tags.Arcane, Level.Tags.Sorcery, Level.Tags.Conjuration]
        self.range = 50
        self.damage = 13
        self.radius = 3
        self.requires_los = False

        ex = Monsters.GreenSlime()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        #cap purposes
        ex = Monsters.RedSlime()
        self.minion_range = ex.spells[0].range

        self.asset = ["ATGMPack", "icons", "slimeteor"]

        self.upgrades['true'] = (1, 7, "True Meteor", "The ball deals [fire] damage instead of [poison] damage, destroys walls, and summons red slimes.")
        self.upgrades['ultm'] = (1, 5, "Unprecedented Evolution", "The ball only summons one slime per cast, but it has double health and gains two random boss modifiers.")
        self.upgrades['iron'] = (1, 4, "Iron Comet", "The ball deals [physical] damage in addition to [poison] damage and summons [metallic] slimes.")  

    def get_extra_examine_tooltips(self):
        return [self.greenslime(), self.spell_upgrades[0], self.redslime(), self.spell_upgrades[1], self.spell_upgrades[2], self.metalslime()]

    def greenslime(self):
        m = Monsters.GreenSlime()
        CommonContent.apply_minion_bonuses(self, m)
        m.buffs[0].spawner = lambda: self.greenslime()
        return m
    
    def metalslime(self):
        m = BossSpawns.apply_modifier(BossSpawns.Metallic, Monsters.GreenSlime())
        CommonContent.apply_minion_bonuses(self, m)
        m.buffs[0].spawner = lambda: self.metalslime()
        return m

    def redslime(self):
        m = Monsters.RedSlime()
        CommonContent.apply_minion_bonuses(self, m)
        m.buffs[0].spawner = lambda: self.redslime()
        return m
    
    def superslime(self):
        m = Monsters.GreenSlime()
        bossmods = random.sample([m[0] for m in BossSpawns.modifiers], k=2)
        for b in bossmods:
            BossSpawns.apply_modifier(b, m)
        CommonContent.apply_minion_bonuses(self, m)
        m.max_hp *= 2
        m.buffs[0].spawner = lambda: self.superslime_split(bossmods)
        return m
    
    def superslime_split(self, bossmods):
        m = Monsters.GreenSlime()
        for b in bossmods:
            BossSpawns.apply_modifier(b, m)
        CommonContent.apply_minion_bonuses(self, m)
        m.max_hp *= 2
        m.buffs[0].spawner = lambda: self.superslime_split(bossmods)
        return m
        
    def get_description(self):
        return (
            "Call forth a ball of slime from the sky, which affects a [{radius}-tile_radius:radius].\n"
            "Deal [{damage}_poison_damage:poison] to all units in the radius.\n"
            "Summon slimes at empty tiles in the radius."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        has_summoned_super = False
        dt = Level.Tags.Poison
        if self.get_stat('true'):
            dt = Level.Tags.Fire
        for p in self.owner.level.get_points_in_ball(x, y, self.get_stat('radius')):
            u = self.owner.level.get_unit_at(p.x, p.y)
            if self.owner.level.tiles[p.x][p.y].is_wall() and self.get_stat('true'):
                self.owner.level.make_floor(p.x, p.y)
            if u:
                u.deal_damage(self.get_stat('damage'), dt, self)
                if self.get_stat('iron'):
                    u.deal_damage(self.get_stat('damage'), Level.Tags.Physical, self)
            else:
                m = self.greenslime()
                if self.get_stat('true'):
                    m = self.redslime()
                if self.get_stat('iron'):
                    m = self.metalslime()
                if self.get_stat('ultm'):
                    if has_summoned_super:
                        continue
                    m = self.superslime()
                if self.caster.level.can_stand(p.x, p.y, m):
                    self.summon(m, p)
                    has_summoned_super = True

class MedusaBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.owner_triggers[Level.EventOnDamaged] = self.on_damage
        self.global_triggers[Level.EventOnSpellCast] = self.on_spell_cast
        self.color = Level.Tags.Nature.color
        self.name = "Medusa Form"
        self.stack_type = Level.STACK_TYPE_TRANSFORM
        self.transform_asset = ["ATGMPack", "units", "medusa_player"]
        self.counter = 0
        self.step = 3

    def snakegen(self):
        while self.counter >= self.step:
            m = self.spell.snake_base()
            if self.spell.get_stat('deadly'):
                m = self.spell.snake_dark()
            self.summon(m, self.owner)
            self.counter -= self.step

    def on_damage(self, evt):
        self.counter += evt.damage
        self.snakegen()

    def on_spell_cast(self, evt):
        if evt.caster == self.owner or evt.x != self.owner.x or evt.y != self.owner.y:
            return
        b = CommonContent.PetrifyBuff() if not self.spell.get_stat('mirror') else CommonContent.GlassPetrifyBuff()
        evt.caster.apply_buff(b, 3)
        if self.spell.get_stat('deadly'):
            evt.caster.deal_damage(5+self.spell.get_stat('damage'), Level.Tags.Dark, self.spell)

class Snakebounce(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Snake Reflect"
        self.color = Level.Tags.Glass.color
        self.buff_type = Level.BUFF_TYPE_PASSIVE
        self.owner_triggers[Level.EventOnPreDamaged] = self.reflect

    def reflect(self, evt):
        victim = evt.source if type(evt.source) == Level.Unit else evt.source.owner
        victim.deal_damage(math.ceil(evt.damage*.75), evt.damage_type, self)

    def get_tooltip(self):
        return "Reflects 75% of damage taken back to the attacker."
        
class MedusaForm(Level.Spell):
    def on_init(self):
        self.name = "Medusa Form"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane, Level.Tags.Nature, Level.Tags.Conjuration]
        self.level = 5
        self.duration = 21
        self.asset = ["ATGMPack", "icons", "medusa_player_ico"]

        ex = Monsters.Snake()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        #for purposes of marksman cap and whatnot
        ex2 = Monsters.GoldenSnake()
        self.minion_range = ex2.spells[0].range

        self.snake_dark = lambda: self.sourceify(Monsters.DeathSnake())

        self.upgrades['spliteye'] = (1, 4, "Descendants' Gaze", "Snakes gain a petrifying gaze with 5 range and a 10 turn cooldown, which petrifies for 3 turns.")
        self.upgrades['deadly'] = (1, 5, "Death Stare", "Enemies that target you take 5 [dark] damage, and death snakes are summoned instead. This effect benefits from [damage] bonuses this spell has.")
        self.upgrades['mirror'] = (1, 6, "Power of Reflection", "Enemies are glassified instead, and snakes deal three-quarters of damage they take back to the attacker.")

    def get_description(self):
        return (
            "Transform into a medusa for [{duration}_turns:duration].\n"
            "Whenever an enemy targets you with an attack, petrify it for [3_turns:duration].\n"
            "For every 3 damage you take while in Medusa Form, summon a snake near you.\n" + text.petrify_desc
        ).format(**self.fmt_dict())

    def sourceify(self, m):
        m.source = self
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def snake_base(self):
        m = Monsters.Snake()
        if self.get_stat('spliteye'):
            s = Monsters.CockatriceGaze()
            s.range = 5
            m.spells.insert(0, s)
        if self.get_stat('mirror'):
            m.buffs.append(Snakebounce())
        m.source = self
        return m

    def cast_instant(self, x, y):
        self.owner.apply_buff(MedusaBuff(self), self.get_stat('duration'))

class InsectPlague(Level.Spell):
    def on_init(self):
        self.name = "Righteous Plague"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Chaos, Level.Tags.Holy, Level.Tags.Nature, Level.Tags.Conjuration]
        self.level = 6
        self.asset = ["ATGMPack", "icons", "righteous_plague"]

        ex = BossSpawns.apply_modifier(BossSpawns.Chaostouched, Monsters.Mantis())
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[1].damage
        self.minion_range = ex.spells[0].range

        self.upgrades['toads'] = (1, 5, "Frog Justice", "Each enemy has a 33% chance to have an infernal horned toad summoned near it, which instantly acts once.")
        self.upgrades['assassinate'] = (2, 7, "Death Knell", "The mantises instead get to instantly act 4 times on summon.")
        self.upgrades['firstborn'] = (1, 8, "Slaying Plague", "When you cast this spell, for each unique name among enemies that exist, a random one of them dies.\nThis occurs after mantises have been summoned, but before their instant actions.\nCannot affect enemies that can gain clarity.")

    def get_extra_examine_tooltips(self):
        t = copy.copy(self.spell_upgrades)
        t.insert(0, self.mantis())
        t.insert(2, self.toad())
        return t

    def get_description(self):
        return (
            "Summon an infernal mantis for every enemy unit.\nThen, all mantises summoned instantly act 2 times."
        ).format(**self.fmt_dict())
    
    def mantis(self):
        m = BossSpawns.apply_modifier(BossSpawns.Chaostouched, Monsters.Mantis())
        CommonContent.apply_minion_bonuses(self, m)
        num_imps = (m.max_hp // 15) + 1
        num_imps = max(1, num_imps)
        num_imps = min(num_imps, 10)
        m.buffs[0].num_spawns = num_imps
        return m
    
    def toad(self):
        m = BossSpawns.apply_modifier(BossSpawns.Chaostouched, Monsters.HornedToad())
        CommonContent.apply_minion_bonuses(self, m)
        num_imps = (m.max_hp // 15) + 1
        num_imps = max(1, num_imps)
        num_imps = min(num_imps, 10)
        m.buffs[0].num_spawns = num_imps
        return m

    def cast(self, x, y):
        enemies = [u for u in self.caster.level.units if Level.are_hostile(u, self.caster)]
        random.shuffle(enemies)
        mantises = []
        toads = []
        for e in enemies:
            p = self.caster.level.get_summon_point(e.x, e.y, radius_limit=99, flying=False)
            if not p:
                continue
            m = self.mantis()
            self.summon(m, e, radius=99)
            mantises.append(m)
            yield
            if self.get_stat('toads') and random.random() < .33:
                t = self.toad()
                p = self.caster.level.get_summon_point(e.x, e.y, radius_limit=99, flying=False)
                if not p:
                    continue
                self.summon(t, e, radius=99)
                toads.append(t)
                yield
        random.shuffle(mantises)
        random.shuffle(toads)
        if self.get_stat('firstborn'):
            names_killed = []
            for e in enemies:
                if e.name not in names_killed and not e.gets_clarity:
                    e.kill()
                    names_killed.append(e.name)
                yield
        for m in mantises:
            for _ in range(2+self.get_stat('assassinate')):
                if m.is_alive():
                    m.advance()
            yield
        for t in toads:
            if t.is_alive():
                t.advance()
            yield

class SlowTaxBuff(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.color = Level.Tags.Arcane.color
        self.name = "Hesitation Tax"
        self.act = None
        self.global_triggers[Level.EventOnPreDamaged] = self.tax_dodge
        self.global_triggers[Level.EventOnUnitAdded] = self.propagate

    def tax_dodge(self, evt):
        if self.spell.get_stat('dodgy'):
            dealer = evt.source.owner or evt.source.caster
            if dealer == self.owner and random.random() < .25:
                evt.unit.add_shields(1)

    def propagate(self, evt):
        if not evt.unit.source:
            return
        if evt.unit.source.owner == self.owner and self.spell.get_stat('truth'):
            evt.unit.apply_buff(SlowTaxBuff(self.spell))

    def on_pre_advance(self):
        self.act = self.owner.get_ai_action()

    def on_advance(self):
        if not self.owner.is_alive():
            self.owner.remove_buff(self)
        elif type(self.act) != Level.CastAction:
            self.owner.deal_damage(self.spell.get_stat('damage'), random.choice([Level.Tags.Arcane, Level.Tags.Dark]), self.spell)
        if self.spell.get_stat('collections') and Level.are_hostile(self.owner, self.spell.caster):
            self.spell.summon(self.spell.call_fearface(), self.owner)

class SlowTaxSpell(Level.Spell):
    def on_init(self):
        self.name = "Hesitation Tax"
        self.max_charges = 4
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane, Level.Tags.Dark]
        self.range = 8
        self.level = 4
        self.damage = 7
        self.can_target_empty = False
        self.asset = ["ATGMPack", "icons", "hesitation_tax"]

        self.upgrades['collections'] = (1, 5, "Collections Department", "Affected enemy units have a fearface summoned next to them each turn.")
        self.upgrades['dodgy'] = (1, 7, "Tax Evasion", "Whenever a unit with Hesitation Tax attempts to deal damage, the victim has a 25% chance to gain 1 shield.")
        self.upgrades['truth'] = (1, 6, "Generational Deductible", "Any unit spawned as a result of an ability or buff from an affected target while the target is alive also has Hesitation Tax applied to it.\nUnits spawned from those targets have Hesitation Tax applied to them, and so on.")
    
    def get_extra_examine_tooltips(self):
        t = copy.copy(self.spell_upgrades)
        t.insert(1, self.call_fearface())
        return t

    def get_description(self):
        return (
            "Target unit takes [{damage}:damage] [arcane] or [dark] damage whenever it doesn't cast a spell during its turn, until it dies."
        ).format(**self.fmt_dict())
    
    def call_fearface(self):
        m = Monsters.Fearface()
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if u:
            u.apply_buff(SlowTaxBuff(self))

class ChokeCloud(Level.Cloud):

    def __init__(self, owner, spell):
        Level.Cloud.__init__(self)
        self.owner = owner
        self.duration = spell.get_stat('duration')
        self.name = "Choking Fog"
        self.source = spell
        self.asset = ["ATGMPack", "other_assets", "silencefog"]
        self.spell = spell

    def get_description(self):
        return "Each turn, silences units inside for 3 turns.\nExpires in %d turns." % self.duration

    def on_advance(self):
        u = self.owner.level.get_unit_at(self.x, self.y)
        if u:
            if not Level.are_hostile(u, self.spell.caster) and self.spell.get_stat('mistshape'):
                if u != self.spell.caster and u.shields < 3:
                    u.add_shields(1)
            else:
                u.apply_buff(Level.Silence(), 3)
            if self.spell.get_stat('holy'):
                u.deal_damage(10, Level.Tags.Holy, self)

    def on_expire(self):
        if self.spell.get_stat('fogform') and random.random() < .1:
            self.spell.summon(self.spell.breathstealer(), self)

class FogChokeSpell(Level.Spell):
    def on_init(self):
        self.name = "Choking Fog"
        self.max_charges = 3
        self.level = 5
        self.tags = [Level.Tags.Arcane, Level.Tags.Enchantment, Level.Tags.Nature]
        self.range = 0
        self.duration = 18
        self.requires_los = False
        self.radius = 4

        self.asset = ["ATGMPack", "icons", "silencefog_ico"]

        self.upgrades['fogform'] = (1, 5, "Fog Soul", "Each cloud that expires has a 10% chance to summon a silent specter near its location.")
        self.upgrades['mistshape'] = (1, 5, "Mistshape", "Allies in the fog are not silenced, and instead gain 1 shield to a max of 3. You do not gain shield, but are also not silenced.")
        self.upgrades['holy'] = (1, 6, "Spirit Breath", "The fog deals a fixed 10 [holy] damage to units standing in it each turn.")

    def get_impacted_tiles(self, x, y):
        points = self.caster.level.get_points_in_ball(self.caster.x, self.caster.y, self.get_stat('radius'))
        return [p for p in points if p != Level.Point(self.caster.x, self.caster.y) and Level.distance(self.caster, p) >= self.get_stat('radius') - 1]
    
    def get_extra_examine_tooltips(self):
        t = copy.copy(self.spell_upgrades)
        t.insert(1, self.breathstealer())
        return t
    
    def breathstealer(self):
        m = Monsters.SilentSpecter()
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def get_description(self):
        return (
            "Beckon thick fog on each tile in a [{radius}-tile_ring:radius] around you.\n"
            "The fog silences units that step in it for 3 turns.\n"
            "The fog lasts [{duration}_turns:duration]."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        for t in self.get_impacted_tiles(x, y):
            self.caster.level.add_obj(ChokeCloud(self.caster, self), t.x, t.y)

class TreeflameBuff(Level.Buff):
    def __init__(self, spell, tiles):
        self.spell = spell
        Level.Buff.__init__(self)
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.stack_type = Level.STACK_INTENSITY # to have multiple forest fires
        self.color = Level.Tags.Nature.color
        self.name = "Forest Fire"
        self.tiles = tiles
        self.resists[Level.Tags.Fire] = self.spell.get_stat('safety')
        self.dmg_counter = 0
        self.bushes = []
        self.global_triggers[Level.EventOnDamaged] = self.count
    
    def on_advance(self):
        for _ in range(2):
            if self.tiles == []:
                break
            tgt = self.tiles.pop()
            b = self.spell.burnsprig()
            self.bushes.append(b)
            self.summon(b, tgt, radius=6)
        if self.tiles == [] and not self.spell.get_stat('life'):
            self.owner.remove_buff(self) 
        elif all(not e.is_alive() for e in self.bushes) and self.tiles == []    :
            self.owner.remove_buff(self)

    def on_unapplied(self):
        if self.spell.get_stat('life'):
            while self.dmg_counter >= 40:
                self.summon(self.spell.burntree(), self.owner)
                self.dmg_counter -= 40

    def count(self, evt):
        if evt.source == self.spell and self.spell.get_stat('life'):
            self.dmg_counter += evt.damage

class Treeflame(Level.Spell):
    def on_init(self):
        self.name = "Forest Fire"
        self.max_charges = 2
        self.level = 5
        self.tags = [Level.Tags.Fire, Level.Tags.Enchantment, Level.Tags.Nature, Level.Tags.Conjuration]
        self.range = 12
        self.radius = 25
        self.damage = 2

        ex = Monsters.ThornPlant()
        self.minion_health = ex.max_hp

        self.asset = ["ATGMPack", "icons", "forest_fire_ico"]

        self.upgrades['safety'] = (100, 3, "Fire Safety", "You gain 100 [fire] resist while Forest Fire is active. Bushes also have their [fire] resist set to 100.")
        self.upgrades['life'] = (1, 7, "Rekindle", "Forest Fire is no longer removed from you until all bushes are destroyed.\nOnce all bushes are destroyed, summon a burning treant for every 40 damage dealt to any unit.")
        self.upgrades['kaboom'] = (1, 5, "Untamed Blaze", "Bush explosions gain 2 radius.")

    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['radius'] = self.radius+(self.get_stat('radius') - self.radius)*5
        return d
    
    def get_extra_examine_tooltips(self):
        t = copy.copy(self.spell_upgrades)
        t.insert(0, self.burnsprig())
        t.insert(3, self.burntree())
        return t
    
    def get_description(self):
        return (
            "Sequentially fill a space of [{radius}_tiles:radius] with [burning:fire] spriggan bushes.\n"
            "The explosions from the bushes count as damage from this spell.\n"
            "Unlike most spells, radius bonuses benefit this spell five times as much as normal, and [damage] bonuses increase the bushes' HP by 10 points each (after other bonuses)."
        ).format(**self.fmt_dict())
    
    def get_impacted_tiles(self, x, y):
        tiles = []
        remaining = self.radius+(self.get_stat('radius') - self.radius)*5
        points_to_check = [Level.Point(x,y)]
        for p in points_to_check:
            if p in tiles or remaining == 0 or not self.caster.level.is_point_in_bounds(p) or not self.caster.level.can_stand(p.x, p.y, self.burnsprig()):
                pass
            elif not self.caster.level.tiles[p.x][p.y].is_wall():
                tiles.append(p)
                remaining -= 1
                points_to_check.append(Level.Point(p.x+1,p.y))
                points_to_check.append(Level.Point(p.x-1,p.y))
                points_to_check.append(Level.Point(p.x,p.y+1))
                points_to_check.append(Level.Point(p.x,p.y-1))
                points_to_check.append(Level.Point(p.x+1,p.y-1))
                points_to_check.append(Level.Point(p.x-1,p.y-1))
                points_to_check.append(Level.Point(p.x-1,p.y+1))
                points_to_check.append(Level.Point(p.x+1,p.y+1))
        return tiles
    
    def burnsprig(self):
        m = Monsters.ThornPlant()
        CommonContent.apply_minion_bonuses(self, m)
        m.max_hp += 10*self.get_stat('damage')
        BossSpawns.apply_modifier(BossSpawns.Flametouched, m)
        m.buffs = m.buffs[1:]
        m.resists[Level.Tags.Fire] = 100*self.get_stat('safety')
        m.turns_to_death = 2
        def new_explode(level, x, y):
            for stage in Level.Burst(m.buffs[1].owner.level, m.buffs[1].owner, m.buffs[1].radius):
                for point in stage:
                    m.buffs[1].owner.level.deal_damage(point.x, point.y, m.buffs[1].damage, m.buffs[1].damage_type, self)
                yield
        m.buffs[1].explode = new_explode
        if self.get_stat('kaboom'):
            m.buffs[1].radius += 2
        m.buffs[1].description = "On death, deals %d %s damage to all tiles in a radius of %d" % (m.buffs[1].damage, m.buffs[1].damage_type.name, m.buffs[1].radius)
        return m
    
    def burntree(self):
        m = Monsters.Treant()
        CommonContent.apply_minion_bonuses(self, m)
        BossSpawns.apply_modifier(BossSpawns.Flametouched, m)
        return m
    
    def cast_instant(self, x, y):
        self.owner.apply_buff(TreeflameBuff(self, self.get_impacted_tiles(x, y)))

class ZPulseDOT(Level.Buff):
    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.spell = spell
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.color = Level.Tags.Ice.color
        self.name = "Absolute Chill"
        self.owner_triggers[Level.EventOnBuffApply] = self.extend
    
    def on_advance(self):
        self.owner.deal_damage(self.spell.get_stat('damage'), Level.Tags.Ice, self.spell)
        if self.spell.get_stat('affliction'):
            self.owner.deal_damage(self.spell.get_stat('damage'), Level.Tags.Poison, self.spell)

    def extend(self, evt):
        if self.spell.get_stat('brittle') and evt.buff.buff_type == Level.BUFF_TYPE_CURSE and evt.buff.duration > 0:
            evt.buff.turns_left = math.ceil(evt.buff.turns_left*1.5)

class ZPulse(Level.Spell):
    def on_init(self):
        self.name = "Zero Pulse"
        self.max_charges = 2
        self.level = 8
        self.tags = [Level.Tags.Enchantment, Level.Tags.Ice]
        self.range = 0
        self.radius = 13
        self.damage = 24
        self.duration = 8

        self.asset = ["ATGMPack", "icons", "zero_pulse"]

        self.upgrades['affliction'] = (1, 4, "Afflicting Cold", "The pulse also deals [poison] damage.")
        self.upgrades['brittle'] = (1, 5, "Whiteout", "If a unit with Absolute Chill has another debuff applied to it, that debuff's duration is extended by 50%.")
        self.upgrades['aqua'] = (1, 5, "Drenching Pulse", "Units affected are [soaked:ice] for 8 turns before this spell's other effects are applied to them.")

    def get_impacted_tiles(self, x, y):
        return [p for stage in Level.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius')) for p in stage]

    def get_description(self):
        return(
            "Emit a pulse of absolute cold which affects a [{radius}-tile_burst:radius].\n"
            "All units in the pulse's area have all of their ability cooldowns permanently increased by 3.\n"
            "Each unit is also given Absolute Chill, which deals [{damage}_ice_damage:ice] each turn for [{duration}_turns:duration].\n"
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        affected = [] #prevents 3x3 units from getting hit 9 times
        for t in self.get_impacted_tiles(self.owner.x, self.owner.y):
            u = self.owner.level.get_unit_at(t.x, t.y)
            if u == self.caster or not u or u in affected:
                continue
            if self.get_stat('aqua'):
                u.apply_buff(CommonContent.SoakedBuff(), 8  )
            for s in u.spells:
                s.cool_down += 3
            u.apply_buff(ZPulseDOT(self), self.get_stat('duration'))
            affected.append(u)

class Bardchant(Level.Spell):
    def on_init(self):
        self.name = "Enchanting Melody"
        self.max_charges = 2
        self.level = 6
        self.tags = [Level.Tags.Enchantment]
        self.range = 0
        self.radius = 6
        self.max_channel = 15

        self.asset = ["ATGMPack", "icons", "ench_melody"]

        self.upgrades['haunt'] = (1, 4, "Haunting Song", "Each turn, apply [fear:dark] to enemies in the radius for 2 turns.")
        self.upgrades['max_channel'] = (15, 5, "Double Concert")
        self.upgrades['opener'] = (1, 5, "Opening Act", "Before channeling starts, gain 3 SH and heal [20_HP:heal].")

        self.ench = None

    def get_description(self):
        return (
            "Play an enchanting song using a random level 4 or lower [enchantment] spell which has range higher than 1.\n"
            "The song casts the selected spell for free on enemies in a [{radius}-tile_radius:radius] each turn.\n"
            "Can be channeled for up to [{max_channel}_turns:duration].\n"
            "The effect is repeated each turn the spell is channeled."
        ).format(**self.fmt_dict())
    
    def get_eligibles(self):
        return [s for s in self.caster.spells if Level.Tags.Enchantment in s.tags and s.name != "Enchanting Melody" and s.level <= 4 and s.range > 1]
    
    def can_cast(self, x, y):
        return len(self.get_eligibles()) > 0
    
    def cast(self, x, y, channel_cast=False):
        if not channel_cast:
            self.caster.apply_buff(Level.ChannelBuff(self.cast, Level.Point(x, y)), self.get_stat('max_channel'))
            self.ench = random.choice(self.get_eligibles())
            if self.get_stat('opener'):
                self.caster.add_shields(3)
                self.caster.deal_damage(-20, Level.Tags.Heal, self)
            yield
        else:
            units = self.caster.level.get_units_in_ball(self.caster, self.get_stat('radius'))
            if not units:
                return
            for u in units:
                if u == self.caster or not self.ench.can_cast(u.x, u.y):
                    continue
                self.caster.level.act_cast(self.caster, self.ench, u.x, u.y, pay_costs=False)
                if self.get_stat('haunt') and Level.are_hostile(u, self.caster):
                    u.apply_buff(Level.FearBuff(), 2)
                yield

class TroublerBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.color = Level.Tags.Arcane.color
        self.name = "Troubler Form"
        self.stack_type = Level.STACK_TYPE_TRANSFORM
        self.transform_asset = ["ATGMPack", "units", "mask_player" if not self.spell.get_stat('fear') else "fear_player"]
        self.resists[Level.Tags.Arcane] = 100
        self.resists[Level.Tags.Dark] = 100*self.spell.get_stat('fear')
        self.global_triggers[Level.EventOnDamaged] = self.randomtp
        self.dmg_counter = 0

    def on_advance(self):
        for _ in range(1+self.spell.get_stat('multishot')):
            possible_targets = self.owner.level.units
            possible_targets = [t for t in possible_targets if self.owner.level.are_hostile(t, self.owner)]
            possible_targets = [t for t in possible_targets if self.owner.level.can_see(t.x, t.y, self.owner.x, self.owner.y)]
            if possible_targets:
                target = random.choice(possible_targets)
                troubler_attack = Monsters.Troubler().spells[0]
                if self.spell.get_stat('fear'):
                    troubler_attack = Monsters.Fearface().spells[0]
                troubler_attack.tags.append(Level.Tags.Enchantment)
                troubler_attack.caster = troubler_attack.owner = self.owner
                self.owner.level.act_cast(self.owner, troubler_attack, target.x, target.y, pay_costs=False)

    def randomtp(self, evt):
        if Level.are_hostile(evt.unit, self.owner) and (evt.damage_type == Level.Tags.Arcane or (evt.damage_type == Level.Tags.Dark and self.spell.get_stat('fear'))):
            self.dmg_counter += evt.damage
            CommonContent.randomly_teleport(evt.unit, 3+self.spell.get_stat('range'))

    def on_unapplied(self):
        if self.spell.get_stat('summoning'):
            summons = [Monsters.MindMaggot, Variants.BrainFlies, Monsters.InsanityImp, Monsters.DisplacerBeast]
            while self.dmg_counter > 1:
                summon = random.choice(summons)()
                self.dmg_counter -= summon.max_hp
                self.summon(summon, self.owner, radius=99)
        
class TroubleForm(Level.Spell):
    def on_init(self):
        self.name = "Troublesome Visage"
        self.max_charges = 3
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane]
        self.level = 5
        self.duration = 17
        self.asset = ["ATGMPack", "icons", "mask_player_ico"]
        self.damage = 3

        self.upgrades['fear'] = (1, 4, "Dreadful Visage", "Assume the shape of a fearface instead.\nThe spell uses the fearface's bolt attack instead, and [dark] damage also teleports units.\nGain 100 [dark] resist for the duration as well.")
        self.upgrades['multishot'] = (2, 5, "Genuinely Troublesome", "Each turn, shoot three bolts instead of one.")
        self.upgrades['summoning'] = (1, 6, "Beckon Annoyances", "When Troubler Form wears off, summon brain fly swarms, insanity imps, displacer beasts, and mind maggots based on [arcane] damage dealt to enemies.")

    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['tp_dist'] = 3 + self.get_stat('range')
        return d
    
    def sourceify(self, m):
        CommonContent.apply_minion_bonuses(self, m)
        return m

    def get_description(self):
        return (
            "Assume the shape of the fearsome troubler for [{duration}_turns:duration], gaining 100 [arcane] resist.\n"
            "Whenever an enemy takes [arcane] damage, randomly teleport them up to [{tp_dist}:range] tiles away.\n"
            "Each turn, shoot a troubler's phase bolt at a random enemy in line of sight, dealing [{damage}_arcane_damage:damage] and teleporting hit units up to 3 tiles away.\n"
            "For the purposes of other spells and skills, the phase bolt is treated as an [enchantment] spell."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.owner.apply_buff(TroublerBuff(self), self.get_stat('duration'))

class GlassMeltBuff(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Glass Heat"
        self.color = Level.Tags.Glass.color
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.stack_type = Level.STACK_INTENSITY
    
    def on_advance(self):
        self.owner.deal_damage(3, Level.Tags.Fire, self)

    def on_unapplied(self):
        b = CommonContent.GlassPetrifyBuff()
        self.owner.apply_buff(b, 3)

class LitGlassBuff(Level.Buff):
    def __init__(self, dmg):
        Level.Buff.__init__(self)
        self.name = "Master Heat"
        self.dmg = dmg
        self.color = Level.Tags.Fire.color
        self.global_triggers[Level.EventOnDamaged] = self.powerfire

    def powerfire(self, evt):
        if not (dealer := evt.source.owner):
            return
        if dealer == self.owner:
            if evt.damage_type != Level.Tags.Fire:
                return
            multi = 2 if type(evt.source) == GlassMeltBuff else 1
            self.owner.max_hp += evt.damage*multi
            self.owner.deal_damage(-evt.damage*multi, Level.Tags.Heal, self)
            b = self.owner.get_buff(Monsters.SlimeBuff)
            if not b:
                return
            b.on_advance()
        elif evt.unit == self.owner:
            dealer.deal_damage(2, Level.Tags.Fire, self)

    def get_tooltip(self):
        return "Deals 2 fire damage to attackers. When dealing fire damage, gain that much current and maximum HP, or double if the source was Glass Heat. Attempt to split when dealing [fire] damage."
        

class ShieldGlassBuff(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Regal Barrier"
        self.color = Level.Tags.Arcane.color
        self.owner_triggers[Level.EventOnPreDamaged] = self.defend
        self.blocked = 0

    def defend(self, evt):
        dealer = evt.source.owner
        if not dealer or evt.damage <= 0 or dealer == self.owner or Level.distance(dealer, self.owner) >= 4:
            #4 checks:
            #1. source exists
            #2. damage is positive (to not trigger on heals or immunities)
            #3. source is not the slime
            #4. distance is at most 5
            return
        self.owner.add_shields(1)
        self.blocked += evt.damage
        to_heal = evt.damage//10
        if to_heal > 0:
            self.owner.max_hp += to_heal
            self.owner.deal_damage(-to_heal, Level.Tags.Heal, self)
        b = self.owner.get_buff(Monsters.SlimeBuff)
        if not b:
            return
        while self.blocked >= 10:
            b.on_advance()
            self.blocked -= 10

    def get_tooltip(self):
        return "Blocks damage from sources less than 6 tiles away and adds 10% of it to current and maximum HP, rounded down. Attempts to split once every 10 damage blocked (before resistances)."
    

class TMPRBuff(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Replete Tempering"
        self.color = Level.Tags.Physical.color
        self.owner_triggers[Level.EventOnDamaged] = self.tmpr
        self.blocked = 0

    def tmpr(self, evt):
        dealer = evt.source.owner
        if not dealer or evt.damage <= 0 or evt.damage_type != Level.Tags.Physical:
            return
        self.owner.max_hp += evt.damage // 2
        self.owner.deal_damage(-evt.damage+1, Level.Tags.Heal, self)
        b = self.owner.get_buff(Monsters.SlimeBuff)
        if not b:
            return
        b.on_advance()

    def get_tooltip(self):
        return "50% of physical damage taken is added to maximum HP, and heals for 100% of physical damage taken. Instantly tries to split on taking physical damage."
        

class GlassSlime(Level.Spell):
    def on_init(self):
        self.name = "Burnglass Drop"
        self.max_charges = 7
        self.level = 3
        self.tags = [Level.Tags.Arcane, Level.Tags.Fire, Level.Tags.Conjuration]
        self.range = 5

        self.must_target_walkable = True

        ex = Monsters.GreenSlime()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        self.asset = ["ATGMPack", "icons", "royal_drop_ico"]

        self.upgrades['powerfire'] = (1, 5, "Perfect Burn", "Whenever the drop deals [fire] damage, it gains that much current and max HP and tries to split. If the damage was from Glass Heat, it gains twice as much.\nDrops also gain retaliation dealing 2 [fire] damage.")
        self.upgrades['tmpr'] = (50, 5, "Trial-Tempered Form", "Drops gain 50 [arcane] resist and have their health rounded up to the nearest multiple of 10.\nWhenever a drop takes [physical] damage, it heals for that amount and gains half that much maximum HP, then tries to split.")
        self.upgrades['rupert'] = (1, 7, "Royal Defense", "Damage drops receive from an attacker less than 4 tiles away is automatically blocked, and 10% of that amount is added to the drop's current and maximum HP.\nEach 10 blocked damage causes it to attempt to split one time.")

    def get_extra_examine_tooltips(self):
        return [self.glass_slime()] + self.spell_upgrades

    def glass_slime(self):
        m = Monsters.GreenSlime()
        CommonContent.apply_minion_bonuses(self, m)
        m.tags.extend([Level.Tags.Glass, Level.Tags.Fire])
        m.name = "Drop of Burnglass"
        m.buffs[0] = Monsters.SlimeBuff(self.glass_slime, 'drops of burnglass')
        m.spells[0].description = "Applies Glass Heat for 3 turns, which deals 3 [fire] damage to the target each turn, and inflicts 3 turns of [glassify:glass] when it wears off."
        m.spells[0].damage_type = Level.Tags.Fire
        m.spells[0].buff = GlassMeltBuff
        m.spells[0].buff_duration = 3
        m.spells[0].name = "Glass Smother"
        m.resists[Level.Tags.Physical] = -100
        m.resists[Level.Tags.Fire] = 100
        m.resists[Level.Tags.Arcane]
        m.asset = ["ATGMPack", "units", "royal_drop"]
        if self.get_stat('powerfire'):
            thorn_dmg = 1+(self.get_stat('minion_damage')-self.minion_damage)
            m.buffs.append(LitGlassBuff(thorn_dmg))
        if self.get_stat('tmpr'):
            new_hp = math.ceil(m.max_hp/10)*10
            m.max_hp = new_hp
            m.apply_buff(TMPRBuff())
        if self.get_stat('rupert'):
            m.apply_buff(ShieldGlassBuff())
        return m

    def get_description(self):
        return (
            "Summon a slime-like drop of molten glass on target tile."
        )
    
    def cast_instant(self, x, y):   
        self.summon(self.glass_slime(), Level.Point(x, y))

class ShenLong(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Shen Long"
        self.level = 6
        self.description = "Whenever you cast your first [conjuration] spell that is not [dragon] each realm, for the rest of the realm, any units it summons are immediately affected by Bequeath Scales."
        self.owner_triggers[Level.EventOnUnitAdded] = self.use
        self.global_triggers[Level.EventOnUnitAdded] = self.give
        self.owner_triggers[Level.EventOnSpellCast] = self.select
        self.has_picked = False
        self.selected_spell = None

    def use(self, evt):
        if evt.unit == self.owner:
            self.has_picked = False
            return
        
    def give(self, evt):
        if evt.unit.source != self.selected_spell or evt.unit == self.owner:
            return
        sp = self.owner.get_spell(DracoRitual)
        if not sp:
            return
        sp.dragonize(evt.unit)

    def select(self, evt):
        if evt.caster != self.owner:
            return
        if Level.Tags.Conjuration not in evt.spell.tags or Level.Tags.Dragon in evt.spell.tags or self.has_picked:
            return
        self.selected_spell = evt.spell
        self.has_picked = True

class DracoRitual(Level.Spell):
    def on_init(self):
        self.name = "Bequeath Scales"
        self.max_charges = 2
        self.level = 6
        self.tags = [Level.Tags.Enchantment, Level.Tags.Nature, Level.Tags.Dragon]
        self.range = 0
        self.radius = 8
        self.max_channel = 6

        self.asset = ["ATGMPack", "icons", "bequeath_scales"]

        self.add_upgrade(ShenLong())
        self.upgrades['max_channel'] = (-2, 3, "Hasty Rite", "Bequeath Scales requires 2 less turns of channeling.")
        self.upgrades['bond'] = (1, 4, "Wyrmbond", "Bequeath Scales also grants permanent wyrm regeneration healing 8 HP each turn.")

    def get_description(self):
        return (
            "Perform a draconic rite, which must be channeled for [{max_channel}_turns:duration].\n"
            "When the rite ends, allies in a [{radius}-tile_radius:radius] gain [dragon] and flight permanently.\n"
        ).format(**self.fmt_dict())
    
    def dragonize(self, unit):
        unit.flying = True
        if Level.Tags.Dragon not in unit.tags:
            unit.tags.append(Level.Tags.Dragon)
        if self.get_stat('bond'):
            unit.apply_buff(CommonContent.RegenBuff(8))
    
    def cast(self, x, y, channel_cast=False):
        if not channel_cast:
            self.caster.apply_buff(Level.ChannelBuff(self.cast, Level.Point(x, y)), self.get_stat('max_channel'))
            yield
        elif not self.owner.has_buff(Level.ChannelBuff):
            units = self.caster.level.get_units_in_ball(self.caster, self.get_stat('radius'))
            if not units:
                return
            for u in units:
                if u == self.caster or Level.are_hostile(self.caster, u):
                    continue
                self.dragonize(u) 
                u.deal_damage(0, Level.Tags.Fire, self)
                yield    

class FairyHallucination(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Great Fairy Hallucination"
        self.level = 7
        self.description = "The first 3 casts of this spell each realm also cause you to cast your Fae Court on yourself."
        self.owner_triggers[Level.EventOnSpellCast] = self.freecast
        self.owner_triggers[Level.EventOnUnitAdded] = self.reset
        self.has_used = 0

    def freecast(self, evt):
        if type(evt.spell) != MindSuck or self.has_used >= 3:
            return
        sp = self.owner.get_spell(Spells.FaeCourt)
        if not sp:
            sp = Spells.FaeCourt()
            sp.owner = sp.caster = self.owner
        self.owner.level.act_cast(self.owner, sp, self.owner.x, self.owner.y, pay_costs=False)
        self.has_used += 1
        
    def reset(self, evt):
        self.has_used = 0


class MindSuck(Level.Spell):
    def on_init(self):
        self.name = "Mind Siphon"
        self.max_charges = 5
        self.tags = [Level.Tags.Enchantment, Level.Tags.Arcane, Level.Tags.Dark, Level.Tags.Sorcery]
        self.range = 9
        self.level = 4
        self.damage = 13
        self.can_target_empty = False
        self.asset = ["ATGMPack", "icons", "mind_suck"]

        self.upgrades['poisonous'] = (1, 3, "Corrode Mind", "Also deal [poison] damage to the target.")
        self.upgrades['refunnel'] = (1, 4, "Reverse Funnel", "If targeting an ally, instead reduce a random cooldown greater than 1 by 1, then deal 3 [dark] and [arcane] damage to yourself.")
        self.add_upgrade(FairyHallucination())
    
    def get_description(self):
        return (
            "Deal [{damage}:damage] dark and arcane damage to the target, and increase the cooldown of one of its abilities by 1 permanently."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if u:
            dts = [Level.Tags.Dark, Level.Tags.Arcane]
            if self.get_stat('poisonous'):
                dts.append(Level.Tags.Poison)
            for dt in dts:
                u.deal_damage(self.get_stat('damage'), dt, self)
            if not u.spells:
                return
            if self.get_stat('refunnel') and not Level.are_hostile(u, self.caster):
                valids = [s for s in u.spells if s.cool_down > 1]
                if not valids:
                    return
                sp = random.choice(valids)
                sp.cool_down -= 1
                for dt in dts:
                    self.caster.deal_damage(3, dt, self)
            else:
                sp = random.choice(u.spells)
                sp.cool_down += 1

class LSplit(Level.Buff):
    def __init__(self, spawner, name, spell):
        Level.Buff.__init__(self)
        self.name = "Capacitant Body"
        self.color = Level.Tags.Lightning.color
        self.spawner = spawner
        self.sn = name
        self.spell = spell
        self.global_triggers[Level.EventOnDamaged] = self.slime

    def on_applied(self, owner):
        self.divisor = 2-0.5*self.spell.get_stat('necro')
        self.to_split = self.owner.max_hp*self.divisor
        self.description = "Gains current and max HP equal to half of the lightning damage it deals. Splits into 2 %ss on reaching %d HP." % (self.sn, self.to_split)

    def slime(self, evt):
        dealer = evt.source.owner
        if not dealer or dealer != self.owner or evt.damage_type != Level.Tags.Lightning:
            return
        self.owner.max_hp += evt.damage // 2
        self.owner.deal_damage(-evt.damage // 2, Level.Tags.Heal, self)
        self.check_split()
    
    def on_advance(self):
        self.check_split()

    def check_split(self):
        if self.owner.cur_hp >= self.to_split:
            self.summon(self.spawner(), self.owner)
            self.owner.max_hp //= self.divisor
            self.owner.cur_hp //= self.divisor

class ShieldCharge(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Shield Charger"
        self.color = Level.Tags.Lightning.color
        self.global_triggers[Level.EventOnDamaged] = self.slime
        self.dmg = 0

    def slime(self, evt):
        dealer = evt.source.owner
        if not dealer or dealer != self.owner or evt.damage_type != Level.Tags.Lightning:
            return
        self.dmg += evt.damage
        while self.dmg >= 10 and self.owner.shields < 3:
            self.dmg -= 10
            self.owner.add_shields(1)

    def get_tooltip(self):
        return "Gains 1 SH for every 10 lightning damage it deals, to a max of 3."

class ElectricBurst(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Burst Retaliation"
        self.color = Level.Tags.Lightning.color
        self.owner_triggers[Level.EventOnDamaged] = self.emit

    def emit(self, evt):
        dealer = evt.source.owner
        if not dealer or dealer == self.owner or dealer not in self.owner.level.get_units_in_ball(self.owner, 2):
            return
        for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, 2):
            if p.y == self.owner.y and p.x == self.owner.x:
                continue
            for dt in [Level.Tags.Lightning]:
                self.owner.level.deal_damage(p.x, p.y, 6, dt, self)
        self.owner.max_hp -= 2
        if self.owner.max_hp <= 0:
            self.owner.kill()
        self.owner.cur_hp = min(self.owner.cur_hp, self.owner.max_hp)

    def get_tooltip(self):
        return "Discharges when attacked by an attacker in 2 tiles, dealing lightning damage and losing 2 max HP."

class LightningSlime(Level.Spell):
    def on_init(self):
        self.name = "Capacitant Gel"
        self.max_charges = 3
        self.level = 4
        self.tags = [Level.Tags.Lightning, Level.Tags.Conjuration]
        self.range = 13

        self.must_target_walkable = True

        ex = Monsters.GreenSlime()
        self.minion_health = ex.max_hp
        self.minion_damage = 5
        self.minion_range = 5

        self.asset = ["ATGMPack", "icons", "capacitant_gel_ico"]

        self.upgrades['repeller'] = (1, 4, "Repel Gel", "Gels' leaps are phasing and gain 2 damage per square traveled.\nGels also become immune to [physical] and can fly.")
        self.upgrades['flash'] = (1, 6, "Flash Pulse", "Whenever a gel is damaged by an attacker in a 2-tile radius of it, it lets out a burst of electricity that deals 6 [lightning] damage.\nThe gel loses 2 max HP afterwards.")
        self.upgrades['guard'] = (1, 5, "Shield Charger", "The gels gain 1 [SH:shield] to a max of 3 for every 10 [lightning] damage they deal.")
        self.upgrades['necro'] = (1, 6, "Ether Capacitor", "The gels become [holy] [undead] and only need to reach 150% of their original max HP to split, as opposed to double.")

    def can_cast(self, x, y):
        return self.caster.level.can_stand(x, y, self.electro_slime())

    def get_extra_examine_tooltips(self):
        return [self.electro_slime()] + self.spell_upgrades

    def electro_slime(self):
        m = Monsters.GreenSlime()
        m.name = "Capacitant Gel"
        m.tags.append(Level.Tags.Lightning)
        m.resists[Level.Tags.Lightning] = 100
        charge =  CommonContent.LeapAttack(self.minion_damage, self.minion_range, damage_type=Level.Tags.Lightning)
        charge.name = "Ionic Charge"
        if self.get_stat('repeller'):
            charge.ghost = True
            charge.charge_bonus = 2
            m.resists[Level.Tags.Physical] = 100
            m.flying = True
        m.spells = [charge, CommonContent.SimpleMeleeAttack(2, damage_type=Level.Tags.Lightning)]
        m.buffs = [LSplit(self.electro_slime, "capacitant gel", self)]
        if self.get_stat('flash'):
            m.buffs.append(ElectricBurst())
        if self.get_stat('guard'):
            m.buffs.append(ShieldCharge())
        if self.get_stat('necro'):
            m.tags.extend([Level.Tags.Undead, Level.Tags.Holy])
        CommonContent.apply_minion_bonuses(self, m)
        m.asset = ["ATGMPack", "units", "capacitant_gel"]
        return m

    def get_description(self):
        return (
            "Summon a capacitant gel on target tile."
        )
    
    def cast_instant(self, x, y):   
        self.summon(self.electro_slime(), Level.Point(x, y))


class WordWrath(Level.Spell):
    def on_init(self):
        self.name = "Word of Wrath"
        self.max_charges = 1
        self.range = 0
        self.tags = [Level.Tags.Fire, Level.Tags.Word]
        self.level = 7
        self.asset = ["ATGMPack", "icons", "word_of_wrath"]
        self.duration = 6

        self.upgrades['burn'] = (1, 4, "Burning Anger", "Each ally in a 3-tile radius that is not [fire] is given the [burning:fire] modifier.")
        self.upgrades['punish'] = (1, 3, "Wrath of the Skies", "Any unit that is weak to [holy] takes [holy] damage instead of getting any other effect from this spell.")
        self.upgrades['revenge'] = (1, 2, "Unfounded Revenge", "Can be cast at full HP, in which case missing HP is treated as 25.")
    
    def can_cast(self, x, y):
        return self.caster.cur_hp != self.caster.max_hp and not self.get_stat('revenge')

    def get_description(self):
        return (
            "Deal [fire] damage to all [living] and [ice] units except the caster equal to the caster's missing HP.\n"
            "All [fire] units are healed for that amount and instantly get another action.\n"
            "All other units gain bloodrage for [{duration}_turns:duration].\n"
            "Cannot be cast if at full HP."
        ).format(**self.fmt_dict())

    def cast(self, x, y):
        units = [u for u in self.caster.level.units]
        random.shuffle(units)
        dmg = self.caster.max_hp - self.caster.cur_hp
        if dmg == 0 and self.get_stat('revenge'):
            dmg = 25
        if self.get_stat('burn'):
            eligibles = [u for u in self.caster.level.get_units_in_ball(self.caster, 3) if not (Level.are_hostile(u, self.caster) or Level.Tags.Fire in u.tags) and u != self.caster]
            for e in eligibles:
                BossSpawns.apply_modifier(BossSpawns.Flametouched, e)
                e.Anim = None
        for u in units:
            if u == self.caster:
                continue
            if Level.Tags.Fire in u.tags:
                if self.get_stat('punish') and u.resists(Level.Tags.Holy) < 0:
                    u.deal_damage(dmg, Level.Tags.Holy, self)
                else:
                    u.deal_damage(-dmg, Level.Tags.Heal, self)
                    u.advance()
            elif Level.Tags.Living in u.tags or Level.Tags.Ice in u.tags:
                dt = Level.Tags.Fire if not(self.get_stat('punish') and u.resists[Level.Tags.Holy] < 0) else Level.Tags.Holy
                u.deal_damage(dmg, dt, self)
            else:
                if self.get_stat('punish') and u.resists(Level.Tags.Holy) < 0:
                    u.deal_damage(dmg, Level.Tags.Holy, self)
                else:
                    u.apply_buff(CommonContent.BloodrageBuff(5), self.get_stat('duration'))
            yield

class SandBreath(Monsters.BreathWeapon):
    def on_init(self):
        self.name = "Sand Breath"
        self.damage = 6
        self.damage_type_list = [Level.Tags.Fire, Level.Tags.Physical]

    def get_description(self):
        return "Breathes a cone of heated sand dealing %d [fire] or [physical] damage. Hits an additional time against [living] and [construct] units." % self.damage

    def per_square_effect(self, x, y):
        iter = 1
        u = self.caster.level.get_unit_at(x, y)
        if (u and (Level.Tags.Living in u.tags or Level.Tags.Construct in u.tags)):
            iter += 1
        for _ in range(iter):
            damage_type = random.choice(self.damage_type_list)
            self.caster.level.deal_damage(x, y, self.damage, damage_type, self)

class Fulgurdrake(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Fulgurdrake"
        self.level = 6
        self.description = "Whenever a sand drake summoned by this spell deals [physical] damage to an enemy, if the target is not [glassified:glass], the drake deals the same amount of [lightning] damage and [glassifies:glass] the target for [3_turns:duration]." + text.glassify_desc
        self.global_triggers[Level.EventOnDamaged] = self.proc

    def proc(self, evt):
        dealer = evt.source.owner
        if dealer.source != self.owner.get_spell(SandDragon) or evt.damage_type != Level.Tags.Physical:
            return
        if evt.unit.has_buff(CommonContent.GlassPetrifyBuff):
            return
        if not Level.are_hostile(evt.unit, self.owner):
            return
        evt.unit.deal_damage(evt.damage, Level.Tags.Lightning, evt.source)
        evt.unit.apply_buff(CommonContent.GlassPetrifyBuff(), 3)

class KingAura(CommonContent.DamageAuraBuff):

    def __init__(self):
        CommonContent.DamageAuraBuff.__init__(self, damage=3, damage_type=[Level.Tags.Fire, Level.Tags.Physical], radius=5)

    def on_hit(self, unit):
        if Level.Tags.Living in unit.tags or Level.Tags.Construct in unit.tags:
            unit.deal_damage(1, Level.Tags.Lightning, self)

    def get_tooltip(self):
        return "Eternal sandstorm deals 3 [fire] or [physical] damage to units in a 5 tile radius. Living and construct units take 1 additional [lightning] damage."

class SandDragon(Level.Spell):
    def on_init(self):
        self.name = "Sand Drake"
        self.max_charges = 2
        self.level = 5
        self.tags = [Level.Tags.Nature, Level.Tags.Dragon, Level.Tags.Conjuration]
        self.range = 5
        self.asset = ["ATGMPack", "icons", "sand_drake_ico"]

        self.must_target_empty = True

        ex = Monsters.FireDrake()

        self.minion_health = 45
        self.minion_damage = ex.spells[1].damage
        self.breath_damage = ex.spells[0].damage
        self.minion_range = ex.spells[0].range

        self.add_upgrade(Fulgurdrake())
        self.upgrades['variant'] = (1, 3, "Mystic Drake", "Summoned sand drakes become [fae:arcane].")
        self.upgrades['ultimate'] = (1, 7, "Great King of Dunes", "Summoned sand drakes have an eternal sandstorm around them which deals 3 [fire] or [physical] damage each turn to enemies in a 5-tile radius.\n[Living] and [construct] units also take 1 [lightning] damage.")

    def get_description(self):
        return "Summon a sand drake at target tile."
    
    def get_extra_examine_tooltips(self):
        return [self.drake()] + self.spell_upgrades
    
    def drake(self):
        m = Monsters.FireDrake()
        m.resists[Level.Tags.Ice] = 0
        m.resists[Level.Tags.Physical] = 25
        m.resists[Level.Tags.Fire] = 50
        m.spells[0] = SandBreath()
        CommonContent.apply_minion_bonuses(self, m)
        m.name = "Sand Drake"
        m.asset = ["ATGMPack", "units", "sand_drake"]
        m.max_hp = self.get_stat('minion_health')
        m.spells[0].damage = self.get_stat('breath_damage')
        m.spells[0].range = self.get_stat('minion_range')
        m.spells[1].damage = self.get_stat('minion_damage')
        m.tags.remove(Level.Tags.Fire)
        m.tags.append(Level.Tags.Nature)
        if self.get_stat('variant'):
            BossSpawns.apply_modifier(BossSpawns.Faetouched, m)
        if self.get_stat('ultimate'):
            m.buffs.append(KingAura())
        return m
    
    def cast_instant(self, x, y):
        self.summon(self.drake(), Level.Point(x, y))

class GlassBolt(Level.Spell):
    def on_init(self):
        self.name = "Fulgurstrike"
        self.max_charges = 3
        self.tags = [Level.Tags.Enchantment, Level.Tags.Lightning, Level.Tags.Nature, Level.Tags.Sorcery]
        self.range = 7
        self.requires_los = False
        self.level = 4
        self.damage = 12
        self.radius = 1
        self.duration = 8
        self.asset = ["ATGMPack", "icons", "fulgurstrike"]

        self.upgrades['radius'] = (2, 5, "Gigantic Bolt")
        self.upgrades['watery'] = (1, 4, "Tidestrike", "Also [soak:ice] targets for the same duration.")
        self.upgrades['fiery'] = (1, 4, "Scorchstrike", "Deal [fire] damage to units before [glassifying:glass] them.")

    def get_impacted_tiles(self, x, y):
        return [p for stage in Level.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius')) for p in stage]
    
    def get_description(self):
        return (
            "Strike an area with sandy lightning, dealing [{damage}:damage] [physical] and [lightning] damage in a [{radius}-tile_burst:radius].\n"
            "Hit units are [glassified:glass] for [{duration}_turns:duration], then dealt another [{damage}_physical_damage:physical].\n"
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        dts = [Level.Tags.Physical, Level.Tags.Lightning]
        for t in self.get_impacted_tiles(x, y):
            for dt in dts:
                self.caster.level.deal_damage(t.x, t.y, self.get_stat('damage'), dt, self)
            u = self.caster.level.get_unit_at(t.x, t.y)
            if u:
                if self.get_stat('fiery'):
                    u.deal_damage(self.get_stat('damage', Level.Tags.Fire, self))
                u.apply_buff(CommonContent.GlassPetrifyBuff(), self.get_stat('duration'))
                if self.get_stat('watery'):
                    u.apply_buff(CommonContent.SoakedBuff(), self.get_stat('duration'))
                u.deal_damage(self.get_stat('damage'), Level.Tags.Physical, self)


class Fundraiser(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.stack_type = Level.STACK_INTENSITY
        self.tag_bonuses[Level.Tags.Metallic]['minion_health'] = 2
        self.name = "Raised Funds"
        self.color = Level.Tags.Metallic.color

class HoardSummon(Level.Spell):
    def on_init(self):
        self.name = "Blood Money"
        self.tags = [Level.Tags.Blood, Level.Tags.Dark, Level.Tags.Conjuration, Level.Tags.Metallic]
        self.level = 5
        self.max_channel = 5
        self.max_charges = 2
        self.minion_health = 3
        self.minion_damage = 6
        self.hp_cost = 35
        self.range = 0

        self.asset = ["ATGMPack", "icons", "blood_money"]

        self.upgrades['zomb'] = (1, 5, "Dead Money", "The piles are [liches:dark].")
        self.upgrades['arm'] = (1, 6, "Arms Investment", "Also summon a pile for each piece of equipment you have.")
        self.upgrades['hp_cost'] = (-35, 4, "Legitimacy", "Blood Money no longer costs HP to cast.")
        self.upgrades['channelboost'] = (3, 6, "Fundraising Round", "Channeling takes an extra 3 turns, but apply a stack of Raised Funds to yourself each turn for 10 turns while channeling.\nRaised Funds increases [minion_health:minion_health] of metallic spells and skills by 2.")

    def get_description(self):
        return (
            "Channel this spell for [{max_channel}_turns:duration], then summon a pile of riches for each consumable you have.\n"
        ).format(**self.fmt_dict())
    
    def coins(self):
        unit = Level.Unit() 
        unit.name = "Pile of Riches"
        unit.max_hp = 3
        unit.shields = 3
        unit.resists[Level.Tags.Physical] = 100
        unit.resists[Level.Tags.Fire] = -50
        bronze = CommonContent.SimpleRangedAttack(damage=6, damage_type=Level.Tags.Lightning, buff=Level.Stun, buff_duration=1, radius=2, range=4, cool_down=4)
        bronze.name = "Bronze Sphere"
        silver = CommonContent.SimpleRangedAttack(damage=6, range=11, beam=True, damage_type=Level.Tags.Physical, cool_down=4)
        silver.name = "Silver Beam"
        gold = CommonContent.HealAlly(heal=9, range=9)
        gold.cool_down = 4
        gold.name = "Gold Gift"
        unit.spells = [bronze, silver, gold]
        unit.buffs.append(CommonContent.ShieldRegenBuff(3, 6))
        unit.asset = ["ATGMPack", "units", "hoard_animus"]
        unit.tags = [Level.Tags.Undead, Level.Tags.Metallic]
        if self.get_stat('zomb'):
            BossSpawns.apply_modifier(BossSpawns.Lich, unit)
        CommonContent.apply_minion_bonuses(self, unit)
        return unit
    
    def cast(self, x, y, channel_cast=False):
        if not channel_cast:
            self.caster.apply_buff(Level.ChannelBuff(self.cast, Level.Point(x, y)), self.get_stat('max_channel')+self.get_stat('channelboost'))
            return
        if self.get_stat('channelboost'):
            self.owner.apply_buff(Fundraiser(), 10)
        if not self.caster.has_buff(Level.ChannelBuff):
            num = sum(i.quantity for i in self.caster.items)
            if self.get_stat('arm'):
                num += len(self.caster.equipment.keys()) + len(self.caster.trinkets)
            for _ in range(num):
                self.summon(self.coins(), self.owner, radius=99)
                yield
        yield

class GiantAxe(Level.Spell):
    def on_init(self):
        self.name = "Giant Axe"
        self.max_charges = 15
        self.range = 5
        self.tags = [Level.Tags.Metallic, Level.Tags.Sorcery]
        self.level = 2
        self.damage = 50
        self.asset = ["ATGMPack", "icons", "giant_axe"]

        self.upgrades['throw'] = (1, 5, "Killer Tomahawk", "Giant Axe can be cast on any tile in range. When cast on tiles more than two tiles away, 7% chance per tile further than 2 to critically strike for three times as much damage.")
        self.upgrades['ghost'] = (1, 4, "Phantom Cleaver", "Also deal [dark] and [holy] damage.")
        self.upgrades['fear'] = (1, 3, "Fearsome Weapon", "Apply 3 turns of [fear:dark] to hit units.")

    def can_cast(self, x, y):
        return Level.Spell.can_cast(self, x, y) and (Level.distance(self.caster, Level.Point(x, y), diag=True) == 2 or self.get_stat('throw'))

    def get_description(self):
        return (
            "Swing with a massive axe, dealing [{damage}_physical_damage:physical] to the target. Can only be used on tiles 2 tiles away from the Wizard."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if u:
            dmg = self.get_stat('damage')
            if self.get_stat('throw'):
                critchance = 0.07*(Level.distance(self.caster, Level.Point(x, y), diag=True)-2)
                if critchance and random.random() < critchance:
                    dmg *= 3
                    self.owner.level.combat_log.debug('%s landed a critical hit!' % self.name)
            u.deal_damage(dmg, Level.Tags.Physical, self)
            if self.get_stat('ghost'):
                for dt in [Level.Tags.Dark, Level.Tags.Holy]:
                    u.deal_damage(dmg, dt, self)
            if self.get_stat('fear'):
                u.apply_buff(Level.FearBuff(), 3)


class ScreenDivision(Level.Buff):
    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.name = "Screen Division"
        self.color = Level.Tags.Chaos.color
        self.stack_type = Level.STACK_DURATION if not spell.get_stat('brv') else Level.STACK_INTENSITY
        self.spell = spell
        self.primary_dts = [Level.Tags.Fire, Level.Tags.Lightning, Level.Tags.Physical]
        self.secondary_dts = [Level.Tags.Arcane, Level.Tags.Dark, Level.Tags.Holy]

    def on_advance(self):
        self.owner.level.queue_spell(self.aoe())
        if self.spell.get_stat('brv'):
            self.owner.deal_damage(2, random.choice(self.primary_dts), self)

    def aoe(self):
        endpoints = random.sample([t for t in self.owner.level.iter_tiles()], k=2)
        line = self.owner.level.get_perpendicular_line(endpoints[0], endpoints[1])
        result = set()
        for p in line:
            for q in self.owner.level.get_points_in_rect(p.x-1, p.y-1, p.x+1, p.y+1):
                result.add(q)
        for p in result:
            u = self.owner.level.get_unit_at(p.x, p.y)
            if u and not Level.are_hostile(self.owner, u) and self.spell.get_stat('smart'):
                continue
            finals = [random.choice(self.primary_dts)]
            if self.spell.get_stat('unst'):
                finals.append(random.choice(self.secondary_dts))
            for dt in finals:
                self.owner.level.deal_damage(p.x, p.y, self.spell.get_stat('damage'), dt, self.spell)
                if random.random() < .05:
                    yield

    def on_unapplied(self):
        for _ in range(self.spell.get_stat('num_targets')):
            self.owner.level.queue_spell(self.aoe())

class SplitScreen(Level.Spell):
    def on_init(self):
        self.name = "Screen Divider"
        self.max_charges = 2
        self.range = 0
        self.tags = [Level.Tags.Metallic, Level.Tags.Enchantment, Level.Tags.Chaos]
        self.level = 5
        self.damage = 17
        self.duration = 8
        self.num_targets = 6
        self.asset = ["ATGMPack", "icons", "screen_divider"]

        self.upgrades['unst'] = (1, 5, "Unstable Slash", "Also add [arcane], [dark], or [holy] damage to the slashes.")
        self.upgrades['smart'] = (1, 4, "Restraint", "Screen Division does not damage you or your allies.")
        self.upgrades['brv'] = (1, 6, "Brave Divider", "Screen Division now stacks in intensity, but deals 2 [physical], [lightning], or [fire] damage to you per stack.")

    def get_description(self):
        return (
            "Grant yourself Screen Division for [{duration}_turns:duration], which stacks in duration.\n"
            "Each turn, Screen Division creates a massive slash dealing [{damage}:damage] [fire], [lightning], or [physical] damage to enemies in the area of effect.\n"
            "The area is a random [3-tile_wide:radius] line which extends infinitely across the realm.\n"
            "When Screen Division expires, it creates [{num_targets}:num_targets] slashes."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.caster.apply_buff(ScreenDivision(self), self.get_stat('duration'))

class AttrStealThiefBuff(Level.Buff):
    def __init__(self, attr, amt):
        Level.Buff.__init__(self)
        self.name = "%s Theft" % attr.title().replace('_', ' ')
        self.global_bonuses[attr] = amt
        self.buff_type = Level.BUFF_TYPE_BLESS if amt > 0 else Level.BUFF_TYPE_CURSE
        self.stack_type = Level.STACK_INTENSITY
        self.color = Level.attr_colors[attr]

class SuperThief(Level.Spell):
    def on_init(self):
        self.name = "Grand Theft"
        self.max_charges = 2
        self.range = 8
        self.cascade_range = 8
        self.tags = [Level.Tags.Dark, Level.Tags.Enchantment, Level.Tags.Translocation]
        self.level = 7
        self.duration = 3
        self.asset = ["ATGMPack", "icons", "grand_theft"]

        self.upgrades['sub'] = (1, 6, "Pyramid Scheme", "Grand Theft now steals minion damage and minion range instead.")
        self.upgrades['rad'] = (1, 8, "Radial Robbery", "Grand Theft can also steal radius.")
        self.upgrades['doubleup'] = (1, 7, "Recurring Job", "This spell can hit the same target twice per cast.")

    def can_chain_to(self, u):
        if not u:
            return False
        elif not Level.are_hostile(u, self.caster):
            return False
        adj = self.caster.level.get_points_in_ball(u.x, u.y, 1.5, diag=True)
        return any(self.caster.level.can_stand(p.x, p.y, self.caster) for p in adj)
    
    def can_cast(self, x, y):
        return Level.Spell.can_cast(self, x, y) and self.can_chain_to(self.owner.level.get_unit_at(x, y))

    def get_description(self):
        return (
            "Move next to target enemy unit and steal either 1 [range] or 2 [damage] from it for [{duration}_turns:duration].\n"
            "The stolen stats benefit all spells and skills.\n"
            "This spell cascades to units up to [{cascade_range}:cascade_range] tiles away from the target that have adjacent spaces the Wizard can stand on.\n"
            "Can only be cast if there is at least 1 adjacent empty space next to target unit."
        ).format(**self.fmt_dict())

    def cast(self, x, y):
        unit = self.caster.level.get_unit_at(x, y)
        first_time = True
        already_hit = []
        while unit or first_time:
            if unit:
                self.steal(unit)
                already_hit.append(unit)
                for _ in range(5):
                    yield
                first_time = False
                candidates = [c for c in self.caster.level.units if self.can_chain_to(c) and Level.distance(c, unit) <= self.get_stat('cascade_range') and c != unit]
                candidates = [c for c in candidates if already_hit.count(c) < 1+self.get_stat('doubleup')]
                unit = random.choice(candidates) if candidates else None
            else:
                unit = None
        yield

    def steal(self, unit):
        adj = self.caster.level.get_points_in_ball(unit.x, unit.y, 1.5, diag=True)
        dest = random.choice([p for p in adj if self.caster.level.can_stand(p.x, p.y, self.caster)])
        for p in self.caster.level.get_points_in_line(self.caster, dest):
            color = random.choice([Level.Tags.Dark.color, Level.Tags.Enchantment.color])
            self.caster.level.leap_effect(p.x, p.y, color, self.caster)
        self.caster.level.act_move(self.caster, dest.x, dest.y, teleport=True)
        attrs = ['range', 'damage']
        if self.get_stat('sub'):
            attrs = ['minion_range', 'minion_damage']
        if self.get_stat('rad'):
            attrs.append('radius')
        to_steal = random.choice(attrs)
        mag = 2 if to_steal in ['damage', 'minion_damage'] else 1
        self.caster.apply_buff(AttrStealThiefBuff(to_steal, mag), self.get_stat('duration'))
        unit.apply_buff(AttrStealThiefBuff(to_steal, -mag), self.get_stat('duration'))

class BigBag(Level.Spell):
    def on_init(self):
        self.name = "Giant Bugsack"
        self.max_charges = 3
        self.level = 3
        self.tags = [Level.Tags.Dark, Level.Tags.Nature, Level.Tags.Conjuration]
        self.range = 5

        self.must_target_walkable = True

        ex = Variants.BagOfBugsGiant()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage

        self.asset = ["ATGMPack", "icons", "giant_bugsack"]

        self.upgrades['chaotic'] = (1, 5, "Bag of Hellbeasts", "Summoned bags and flies gain [infernal:chaos] and [demon].")
        self.upgrades['ghost'] = (1, 4, "Bag of Soulflies", "The bags gain [ghostly:dark].")
        self.upgrades['superspawn'] = (1, 3, "Expansive Sack", "The bags' chance to spawn fly swarms each turn increases by 10% per point of [num_summons:num_summons] this spell has.")

    def get_extra_examine_tooltips(self):
        return [self.bugbag(), 
                self.norm_fly(),
                self.spell_upgrades[0],
                self.bugbag_infernal(),
                self.infern_fly(),
                self.spell_upgrades[1],
                self.bugbag_ghost(), 
                self.ghost_fly(),
                self.spell_upgrades[2]
                ]

    def bugbag(self):
        m = Variants.BagOfBugsGiant()
        CommonContent.apply_minion_bonuses(self, m)
        deathspawn = m.get_buff(CommonContent.SpawnOnDeath)
        deathspawn.description = deathspawn.description.replace('4', str(deathspawn.num_spawns))
        m.buffs[1].spawner = lambda: self.norm_fly()
        return m
    
    def norm_fly(self):
        m = Monsters.FlyCloud()
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def infern_fly(self, bonuses=False):
        m = Monsters.FlyCloud()
        BossSpawns.apply_modifier(BossSpawns.Chaostouched, m)
        m.tags.append(Level.Tags.Demon)
        if bonuses:
            CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def ghost_fly(self):
        m = Monsters.FlyCloud()
        BossSpawns.apply_modifier(BossSpawns.Ghostly, m)
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def bugbag_infernal(self):
        m = Variants.BagOfBugsGiant()
        BossSpawns.apply_modifier(BossSpawns.Chaostouched, m)
        deathspawn = m.get_buff(CommonContent.SpawnOnDeath)
        deathspawn.description = deathspawn.description.replace('4', str(deathspawn.num_spawns))
        m.buffs[1].spawner = lambda: self.infern_fly(True)
        m.buffs[0].spawner = lambda: self.infern_fly()
        CommonContent.apply_minion_bonuses(self, m)
        m.tags.append(Level.Tags.Demon)
        return m
    
    def bugbag_ghost(self):
        m = Variants.BagOfBugsGiant()
        BossSpawns.apply_modifier(BossSpawns.Ghostly, m)
        deathspawn = m.get_buff(CommonContent.SpawnOnDeath)
        deathspawn.description = deathspawn.description.replace('4', str(deathspawn.num_spawns))
        m.buffs[1].spawner = lambda: self.ghost_fly()
        CommonContent.apply_minion_bonuses(self, m)
        return m

    def get_description(self):
        return (
            "Summon a giant bag of bugs on target tile."
        )
    
    def cast_instant(self, x, y):   
        m = self.bugbag()
        if self.get_stat('chaotic'):
            m = self.bugbag_infernal()
        if self.get_stat('ghost'):
            m = self.bugbag_ghost()
        if self.get_stat('superspawn'):
            m.buffs[1].spawn_chance += .1*self.get_stat('num_summons')
        self.summon(m, Level.Point(x, y))

class BloodCopyBuff(Level.Buff):
    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.name = "Sanguine Simulacrum"
        self.color = Level.Tags.Blood.color
        self.global_triggers[Level.EventOnUnitAdded] = self.proc
        self.global_bonuses_pct['num_summons'] = 100
        self.spell = spell
        self.global_bonuses['num_summons'] = spell.get_stat('swarm')

    def proc(self, evt):
        if Level.are_hostile(evt.unit, self.owner):
            return
        if self.spell.get_stat('soul') and Level.Tags.Living in evt.unit.tags:
            self.summon(self.spell.ghast(evt.unit.max_hp), evt.unit, radius=99)

class BloodCopy(Level.Spell):
    def on_init(self):
        self.name = "Sanguine Simulacrum"
        self.max_charges = 3
        self.range = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Blood]
        self.level = 6
        self.hp_cost = 50
        self.duration = 3
        self.asset = ["ATGMPack", "icons", "hemocloning"]

        self.upgrades['swarm'] = (1, 4, "Bloodswarm", "Gain 1 [num_summons:num_summons] for the duration as well.")
        self.upgrades['hp_cost'] = (-30, 4, "Improved Process", "Sanguine Simulacrum costs 30 less HP to cast.")
        self.upgrades['soul'] = (1, 4, "Soul Copy", "Whenever you summon a [living] unit while this spell is active, summon a bloodghast with the same HP.")

    def ghast(self, hp=0):
        unit = Monsters.Bloodghast()
        CommonContent.apply_minion_bonuses(self, unit)
        unit.max_hp = hp
        return unit

    def get_extra_examine_tooltips(self):
        return self.spell_upgrades + [self.ghast()]

    def get_description(self):
        return (
            "Gain 100% [num_summons:num_summons] for all spells and skills for [{duration}_turns:duration]."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        self.caster.apply_buff(BloodCopyBuff(self), self.get_stat('duration'))


class ShrinkMinions(Level.Spell):
    def on_init(self):
        self.name = "Travel-Size"
        self.max_charges = 3
        self.range = 10
        self.requires_los = False
        self.tags = [Level.Tags.Enchantment]
        self.level = 7
        self.asset = ["ATGMPack", "icons", "travel_size"]
        self.names_casted_on = []

        self.upgrades['range'] = (5, 3)
        self.upgrades['modify'] = (1, 4, "Tiny Costume", "Travel-Size now reduces maximum HP by 30%.\nIf targeting a unit without a boss modifier, give it a random one.")
        self.upgrades['???'] = (1, 3, "Enigma Purse", "Randomize the creature's tags before turning it into a pet.")

    def can_cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        if Level.are_hostile(u, self.caster) or getattr(u, "is_travel_sized", False) or u.radius:
            return
        return Level.Spell.can_cast(self, x, y) and not u in self.names_casted_on

    def get_description(self):
        return (
            "Shrink target minion into a travel-sized package.\n"
            "It loses 20% of its maximum HP and all SH, but becomes an exotic pet item and sticks around between realms.\n"
            "Once you use this spell on a unit, no units of the same name as the target can be affected by this spell.\n"
            "Cannot target multi-tile units."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        hp_mod = 0.8 - 0.1*self.get_stat('modify')
        u.max_hp = math.floor(u.max_hp*hp_mod)
        u.refresh()
        if self.get_stat('???'):
            u.tags = list(random.sample(list(Level.Tags), random.randint(1, 7)))
        u.kill()
        bossmod = random.choice([m[0] for m in BossSpawns.modifiers])
        def recreate():
            u.Anim = None
            if not u.recolor_primary and self.get_stat('modify'):
                BossSpawns.apply_modifier(u, bossmod)
            u.refresh()
            u.buffs = [b for b in u.buffs if b.buff_type not in [Level.BUFF_TYPE_CURSE, Level.BUFF_TYPE_BLESS]]
            return u
        equ = Equipment.PetCollar(recreate)
        self.caster.equip(equ)
        self.names_casted_on.append(u.name)

class SenselessCast(Level.Spell):
    def on_init(self):
        self.name = "Unimaginable Path"
        self.max_charges = 2
        self.range = 0
        self.requires_los = False
        self.tags = [Level.Tags.Arcane, Level.Tags.Chaos, Level.Tags.Translocation]
        self.level = 8
        self.asset = ["ATGMPack", "icons", "unimaginable_path"]

        self.upgrades['incomp'] = (1, 5, "Unthinkable Strategy", "Randomly teleport instead of moving to locations where spells were cast, but your highest level spell is cast 1 extra time.")
        self.upgrades['planned'] = (1, 5, "Planned Progression", "Spells are cast in increasing level order")
        self.upgrades['pain'] = (1, 4, "Path of Pain", "Whenever Unimaginable Path casts a [blood] spell, cast your Lifedrain for free on a random enemy.\nUnlike most instances of casting your spells, this Lifedrain has 99 range.")

    def get_description(self):
        return (
            "For each spell with nonzero range you know, cast it at a random valid tile for free, then teleport there.\n"
            "Spells are cast in a random order.\n"
            "Unimaginable Path's effect ends early if the chosen spell has no valid tiles to cast it on, or the spell's target tile can't be moved to .\n"
            "[Orb] spells do not cause the user to teleport and will not end the effect if the user can't be teleported to the target tile.\n"
            "Once the spell's effect ends, the wizard is stunned for 1 turn."
        ).format(**self.fmt_dict())

    def cast(self, x, y):
        candidates = [s for s in self.caster.spells if s.range > 0]
        random.shuffle(candidates)
        if not len(candidates):
            return
        if self.get_stat('planned'):
            candidates.sort(key=lambda x: x.level)
        if self.get_stat('incomp'):
            candidates.append(max(candidates, key=lambda x: x.level))
        for c in candidates:
            spots = [t for t in self.caster.level.iter_tiles() if c.can_cast(t.x, t.y)]
            if not spots:
                break
            cast_point = random.choice(spots)
            self.caster.level.act_cast(self.caster, c, cast_point.x, cast_point.y, pay_costs=False)
            if self.get_stat('pain'):
                l = self.caster.get_or_make_spell(Spells.BloodTapSpell)
                l.statholder = self.caster
                l.range = 99
                spots = [t for t in self.caster.level.iter_tiles() if l.can_cast(t.x, t.y)]
                if not len(spots):
                    pass
                else:
                    l_cast_point = random.choice(spots)
                    self.caster.level.act_cast(self.caster, l, l_cast_point.x, l_cast_point.y, pay_costs=False)
            for _ in range(2):
                yield
            tpp = cast_point
            if self.get_stat('incomp'):
                candidates = [t for t in self.caster.level.iter_tiles() if self.caster.level.can_stand(t.x, t.y, self.caster)]
                if not candidates:
                    break
                tpp = random.choice(candidates)
            if not self.caster.level.can_stand(tpp.x, tpp.y, self.caster):
                break
            if Level.Tags.Orb in c.tags:
                continue
            for p in self.caster.level.get_points_in_line(self.caster, tpp, two_pass=False, find_clear=False):
                color = random.choice([Level.Tags.Chaos.color, Level.Tags.Arcane.color])
                self.caster.level.leap_effect(p.x, p.y, color, self.caster)
            self.caster.level.act_move(self.caster, tpp.x, tpp.y, teleport=True)

class CurseOfSalt(Level.Upgrade):

    def on_init(self):
        self.name = "Salted Earth"
        self.description = "Non-flying enemies in 8 tiles can't heal."
        self.color = Level.Tags.Poison.color

    def on_advance(self):
        victims = [u for u in self.owner.level.get_units_in_ball(self.owner, 8) if Level.are_hostile(u, self.owner)]
        for v in victims:
            b = Level.Buff()
            b.color = Level.Tags.Holy.color
            b.name = self.name
            b.resists[Level.Tags.Heal] = -100
            b.buff_type = Level.BUFF_TYPE_CURSE
            v.apply_buff(b, 1)

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
        return "Deals 4 [holy] and [poison] damage to any unit that moves towards it."
    
    def process_unit(self, evt):
        if evt.unit != self.owner:
            self.update_table_entry(evt.unit)
        else:
            for u in self.owner.level.units:
                if u not in self.dist_table.keys():
                    self.update_table_entry(u)
    
    def update_table_entry(self, u):
        self.dist_table[u] = Level.distance(self.owner, u)
    
    def proc_damage(self, evt):
        if evt.unit not in self.dist_table.keys():
            self.update_table_entry(evt.unit)
            return
        if Level.distance(self.owner, Level.Point(evt.x, evt.y)) < self.dist_table[evt.unit]:
            dmg = 4
            if evt.unit.has_buff(CommonContent.SoakedBuff) and self.spell.get_stat('desiccate'):
                evt.unit.deal_damage(2, Level.Tags.Lightning, self)
            for d in [Level.Tags.Holy, Level.Tags.Poison]:
                evt.unit.deal_damage(dmg, d, self)
        self.update_table_entry(evt.unit)
            


class SaltPillar(Level.Spell):
    def on_init(self):
        self.name = "Salt Pillar"
        self.max_charges = 1
        self.level = 7
        self.tags = [Level.Tags.Holy, Level.Tags.Nature, Level.Tags.Conjuration]
        self.range = 2

        self.minion_health = 190
        self.minion_damage = 10

        self.must_target_walkable = True

        self.asset = ["ATGMPack", "icons", "salt_pillar"]

        self.upgrades['desiccate'] = (1, 5, "Pillar of Desiccation", "The pillar deals an extra 2 [lightning] damage to [soaked:ice] targets.")
        self.upgrades['initiative'] = (1, 4, "Preemptive Judgment", "When a pillar is summoned, it casts your Pillar of Fire on the closest enemy.")
        self.upgrades['curse'] = (1, 6, "Earthsalting", "Any non-flying enemy in 8 tiles of the pillar can't heal.")

    def get_extra_examine_tooltips(self):
        return [self.pillar()] + self.spell_upgrades

    def pillar(self):
        u = Level.Unit()
        u.stationary = True
        u.asset = ["ATGMPack", "units", "salt_pillar"]
        u.name = "Pillar of Salt"
        u.tags = [Level.Tags.Nature, Level.Tags.Holy]
        u.max_hp = self.get_stat('minion_health')
        u.resists[Level.Tags.Physical] = 50
        u.resists[Level.Tags.Fire] = 50
        u.resists[Level.Tags.Lightning] = 25
        u.resists[Level.Tags.Holy] = 100
        u.resists[Level.Tags.Poison] = 100
        u.buffs.append(SaltJudgment(self))
        u.spells = [CommonContent.SimpleMeleeAttack(self.get_stat('minion_damage'))]
        if self.get_stat('curse'):
            u.buffs.append(CurseOfSalt())
        return u

    def get_description(self):
        return (
            "Summon a pillar of salt on target tile."
        )
    
    def cast_instant(self, x, y):   
        p = self.summon(self.pillar(), Level.Point(x, y))
        if not p:
            return
        if self.get_stat('initiative'):
            flame = self.caster.get_or_make_spell(Spells.FlameStrikeSpell)
            flame.caster = p
            flame.statholder = self.caster
            flame.should_ai_channel = lambda t: False
            spots = [u for u in self.caster.level.units if flame.can_cast(u.x, u.y) and Level.are_hostile(u, p)]
            random.shuffle(spots)
            spots.sort(key=lambda t: Level.distance(p, t))
            if not spots:
                return
            cast_point = random.choice(spots)
            self.caster.level.act_cast(p, flame, cast_point.x, cast_point.y, pay_costs=False)

class RayPierceSpell(Level.Spell):
    def on_init(self):
        self.name = "Exploding Pierce"
        self.max_charges = 4
        self.tags = [Level.Tags.Sorcery, Level.Tags.Metallic, Level.Tags.Fire]
        self.range = 9
        self.level = 4
        self.damage = 15
        self.radius = 3
        self.requires_los = False

        self.asset = ["ATGMPack", "icons", "exploding_pierce"]

        self.upgrades['damage'] = (17, 5)
        self.upgrades['ghost'] = (1, 4, "Ghost Sniper", "Casting Exploding Pierce gives 2 SH.")
        self.upgrades['sun'] = (1, 6, "Starburst", "The dart stops after the first unit it hits, and instead explodes in a fixed 10 to 25 tile ring around that target.")

    def get_description(self):
        return (
            "Shoot a magic dart which will travel infinitely in the chosen direction, dealing [{damage}_physical_damage:physical] to units in its path.\n"
            "Darts generate explosions around hit units dealing [{damage}_fire_damage:fire] in a [{radius}-tile_radius:radius]."
        ).format(**self.fmt_dict())
    
    #finally, ray targeting
    def get_impacted_tiles(self, x, y):
        start = Level.Point(self.caster.x, self.caster.y)
        dx = (x-self.caster.x)
        dy = (y-self.caster.y)
        result = set()
        for p in Level.Bolt(self.owner.level, start, Level.Point(x+self.owner.level.width*dx, y+self.owner.level.height*dy), False, False):
            if (p.x >= 0 and p.x < self.owner.level.width) and (p.y >= 0 and p.y < self.owner.level.height):
                if p not in result:
                    result.add(p)
            else:
                break
        return list(result)
    
    def cast(self, x, y):
        aoe = self.get_impacted_tiles(x, y) 
        aoe.sort(key=lambda p: Level.distance(p, self.caster))
        for p in aoe:
            self.caster.level.projectile_effect(p.x, p.y, proj_name=    os.path.join("..","..","..","mods","ATGMPack","other_assets","piercer"), proj_origin=self.caster, proj_dest=aoe[-1])
            if (u := self.caster.level.get_unit_at(p.x, p.y)):
                u.deal_damage(self.get_stat('damage'), Level.Tags.Physical, self)
                if not self.get_stat('sun'):
                    for p in self.owner.level.get_points_in_ball(u.x, u.y, self.get_stat('radius')):
                        self.owner.level.deal_damage(p.x, p.y, self.get_stat('damage'), Level.Tags.Fire, self)
                else:
                    points = self.caster.level.get_points_in_ball(p.x, p.y, 25)
                    points = [t for t in points if t != Level.Point(p.x, p.y) and Level.distance(t, p) >= 10]
                    for p3 in points:
                        self.owner.level.deal_damage(p3.x, p3.y, self.get_stat('damage'), Level.Tags.Fire, self)
                    break
            yield
        if self.get_stat('ghost'):
            self.owner.add_shields(2)

class IceShiv(Level.Spell):
    def on_init(self):
        self.name = "In Cold Blood"
        self.max_charges = 3
        self.damage = 34
        self.range = 99
        self.hp_cost = 10
        self.requires_los = False
        self.tags = [Level.Tags.Ice, Level.Tags.Blood, Level.Tags.Sorcery, Level.Tags.Translocation]
        self.level = 5

        self.asset = ["ATGMPack", "icons", "in_cold_blood"]

        self.upgrades['assassin'] = (1, 5, "Assassination", "This spell deals double damage, if doubled damage would kill the target.")
        self.upgrades['thrust'] = (5, 4, "Sonic Thrust", "The distance required for [physical] damage to be dealt is reduced to 5.")
        self.upgrades['hp_cost'] = (-10, 3)

    def can_cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        return Level.Spell.can_cast(self, x, y) and u and not self.caster.level.can_see(self.caster.x, self.caster.y, x, y)

    def get_description(self):
        return (
            "Attack with with a bloody icicle, dealing [{damage}_ice_damage:ice], plus the same amount of [physical] damage if the enemy is more than 10 tiles away.\n"
            "Move next to the target after dealing damage, if possible."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        adj = list(self.caster.level.get_adjacent_points(Level.Point(x, y), True, True))
        adj.sort(key=lambda x: Level.distance(self.caster, x))
        pot = adj[0]
        kill_dist = Level.distance(u, self.caster)
        d = self.get_stat('damage')
        if self.get_stat('assassin'):
            imult = (100 - u.resists[Level.Tags.Ice]) / 100.0
            pmult = (100 - u.resists[Level.Tags.Ice]) / 100.0 if kill_dist >= 10 else 0
            if math.ceil(d*2*imult + d*2*pmult) >= u.cur_hp:
                d *= 2
            self.owner.level.combat_log.debug('%s damage was doubled' % self.name)
        u.deal_damage(d, Level.Tags.Ice, self)
        if kill_dist >= 10 - self.get_stat('thrust'):
            u.deal_damage(d, Level.Tags.Physical, self)
        for p in self.caster.level.get_points_in_line(self.caster, pot):
            color = random.choice([Level.Tags.Blood.color, Level.Tags.Ice.color])
            self.caster.level.leap_effect(p.x, p.y, color, self.caster)
        self.caster.level.act_move(self.caster, pot.x, pot.y, teleport=True)


class BloodElectroBuff(Level.Silence):
    def __init__(self, spell):
        self.spell = spell
        Level.Silence.__init__(self)
        self.name = "Tempest Stance"
        self.color = Level.Tags.Blood.color
        self.owner_triggers[Level.EventOnPreDamaged] = self.counter
        if spell.get_stat('heaven'):
            for dt in [Level.Tags.Holy, Level.Tags.Fire, Level.Tags.Physical, Level.Tags.Lightning]:
                self.resists[dt] = 50

    def counter(self, evt):
        source = evt.source if type(evt.source) == Level.Unit else evt.source.owner
        if not source:
            return
        victims = [u for u in self.owner.level.units if Level.are_hostile(self.owner, u)]
        for v in victims:
            pather = Level.Unit()
            pather.flying = True
            path = self.owner.level.find_path(self.owner, v, pather, pythonize=True, unit_penalty=0)
            for p in path:
                self.owner.level.deal_damage(p.x, p.y, self.spell.get_stat('damage'), Level.Tags.Lightning, self.spell)
                if self.spell.get_stat('doom'):
                    self.owner.level.deal_damage(p.x, p.y, self.spell.get_stat('damage'), Level.Tags.Dark, self.spell)
            if self.spell.get_stat('flux'):
                sp = self.owner.get_or_make_spell(Spells.EssenceFlux)
                self.owner.level.act_cast(self.owner, sp, v.x, v.y, pay_costs=False)

class BloodElectro(Level.Spell):
    def on_init(self):
        self.name = "Tempest Stance"
        self.max_charges = 3
        self.range = 0
        self.tags = [Level.Tags.Lightning, Level.Tags.Blood, Level.Tags.Enchantment]
        self.level = 6
        self.hp_cost = 33
        self.duration = 17
        self.damage = 10

        self.asset = ["ATGMPack", "icons", "tempest_stance"]

        self.upgrades['doom'] = (1, 5, "Shadow Stance", "Deal [dark] damage in the paths as well.")
        self.upgrades['heaven'] = (1, 4, "Divine Technique", "Gain 50 [holy], [lightning], [physical], and [fire] resist for the duration.")
        self.upgrades['flux'] = (1, 4, "Ebbing Storm", "Cast your Essence Flux on each path target.")

    def get_description(self):
        return (
            "Silence yourself for [{duration}_turns:duration].\n"
            "Whenever you take damage from an enemy, deal [{damage}_lightning_damage:lightning] in paths towards all enemies.\n"
            "Lasts [{duration}_turns:duration]."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        self.caster.apply_buff(BloodElectroBuff(self), self.get_stat('duration'))

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
        self.name = "Scale Armor"
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
            if Level.Point(aggressor.x, aggressor.y) in self.owner.level.get_adjacent_points(self.owner, False, False) and evt.damage > 0:
                self.owner.add_shields(1)
                aggressor.deal_damage(evt.damage, evt.damage_type, self.spell)

    def adapt(self, evt):
        if self.spell.get_stat('adapt'):
            self.owner.resists[evt.damage_type] += 15

class RazorScales(Level.Spell):
    def on_init(self):
        self.name = "Scale Armor"
        self.max_charges = 5
        self.tags = [Level.Tags.Enchantment, Level.Tags.Nature, Level.Tags.Dragon]
        self.range = 5
        self.level = 3
        self.damage = 7
        self.can_target_empty = False

        self.asset = ["ATGMPack", "icons", "scale_armor"]

        self.upgrades['mir'] = (1, 7    , "Mirror Armor", "The target automatically blocks and reflects damage from adjacent sources.")
        self.upgrades['adapt'] = (1, 6, "Adaptive Carapace", "Whenever the target takes damage, it gains 15 resistance to that type permanently.")
        self.upgrades['shot'] = (1, 4, "Scale Shot", "The target gains a cone attack dealing double this spell's retaliation damage with a 3 turn cooldown. This attack reduces the user's [physical] resist by 1 per square it targets.")

    def get_description(self):
        return (
            "Target unit gains melee retaliation dealing [{damage}_physical_damage:physical] and 50 [physical] resist."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        u.apply_buff(ScaleThorn(self))

class WeirdSpider(Spells.OrbSpell):
    def on_init(self):
        self.name = "Gasteracantha"
        self.range = 10
        self.max_charges = 3

        self.minion_damage = 6

        self.melt_walls = False

        self.minion_health = 60
        self.minion_damage = 10
        self.radius = 5
        
        self.tags = [Level.Tags.Nature, Level.Tags.Orb, Level.Tags.Conjuration]
        self.level = 5

        self.asset = ["ATGMPack", "icons", "spidorb_ico"]

        self.upgrades['punish'] = (1, 5, "Nephila", "The Cancriformis gains additional retaliation dealing 5 [holy] damage if the Gasteracantha moved 8 or more tiles.")
        self.upgrades['metal'] = (1, 4, "Argiope", "The Cancriformis gains the [metallic] modifier and double HP if the Gasteracantha moved 5 or more tiles.")
        self.upgrades['doom'] = (7, 6, "Herennia", "The Gasteracantha's aura deals increased [dark] damage, and it gains [dark], [metallic], and [undead].")

    def get_extra_examine_tooltips(self):
        return [self.trueform(Level.Unit())] + self.spell_upgrades

    def get_description(self):
        return (
            "Summon the Gasteracantha next to the caster.\n"
            "The Gasteracantha is an spider orb that weaves webs and deals [[{minion_damage}_physical_damage:physical] in a [{radius}-tile_radius:radius].\n"
            "It moves one tile towards the target point each turn, and spawns a Cancriformis on death.\n"
            "The Cancriformis' strength increases based on how many tiles the Gasteracantha moved.\n"
            "The Gasteracantha can be destroyed by [poison] damage.\n"
            ).format(**self.fmt_dict())
        
    def on_make_orb(self, orb):
        orb.resists[Level.Tags.Poison] = 0
        orb.name = "Gasteracantha"
        orb.tags.append(Level.Tags.Spider)
        orb.tags = [Level.Tags.Spider]
        orb.buffs.append(CommonContent.SpawnOnDeath(lambda: self.trueform(orb), 1))
        orb.asset = ["ATGMPack", "units", "spidorb"]
        orb.tiles_moved = 0
        if self.get_stat('doom'):
            orb.tags.extend([Level.Tags.Dark, Level.Tags.Metallic, Level.Tags.Undead])
    
    def trueform(self, orb):
        mov_dist = getattr(orb, "tiles_moved", 0)
        spoder = Level.Unit()
        spoder.max_hp = self.get_stat('minion_health')+10+(4*mov_dist)
        spoder.tags = [Level.Tags.Living, Level.Tags.Spider]
        spoder.spells.append(CommonContent.SimpleMeleeAttack(self.minion_damage+mov_dist, buff=CommonContent.Poison, buff_duration=15))
        spoder.name = "Cancriformis"
        spoder.asset = ["ATGMPack", "units", "cancriformis"]
        spoder.buffs.append(CommonContent.RetaliationBuff(8, Level.Tags.Physical))
        if self.get_stat('punish') and mov_dist >= 8:
            spoder.buffs.append(CommonContent.RetaliationBuff(5, Level.Tags.Holy))
        if self.get_stat('metal') and mov_dist >= 5:
            spoder.max_hp *= 2
            BossSpawns.apply_modifier(BossSpawns.Metallic, spoder)
        return spoder
                
    def on_orb_move(self, orb, next_point):
        for t in self.owner.level.get_tiles_in_ball(orb.x, orb.y, self.get_stat('radius')):
            if random.random() < .35:
                w = CommonContent.SpiderWeb()
                w.owner = orb
                orb.level.add_obj(w, t.x, t.y)
            unit = orb.level.get_unit_at(t.x, t.y)
            if unit and Level.are_hostile(orb, unit):
                dmg = self.get_stat('minion_damage') + self.get_stat('doom')
                dt = Level.Tags.Physical if not self.get_stat('doom') else Level.Tags.Dark
                unit.deal_damage(dmg, dt, self)
        orb.tiles_moved += 1


class Knife(Level.Spell):
    def on_init(self):
        self.name = "Hidden Knife"
        self.max_charges = 20
        self.melee = True
        self.range = 1.5
        self.can_target_empty = False
        self.quick_cast = True
        self.tags = [Level.Tags.Metallic, Level.Tags.Sorcery]
        self.level = 1
        self.damage = 9
        self.asset = ["ATGMPack", "icons", "hidden_knife"]

        self.upgrades['flash'] = (1, 3, "Flash Thrust", "On kill, refreshes your quick cast")
        self.upgrades['mash'] = (1, 3, "Mage Masher", "Silences the target for 3 turns.")
        self.upgrades['ice'] = (1, 4, "Crystal Dagger", "Also deal [ice] and [holy] damage to the target.")

    def get_description(self):
        return (
            "Deal [{damage}:damage] [physical] and [poison] damage to a target in melee range."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        dts = [Level.Tags.Physical, Level.Tags.Poison]
        if self.get_stat('ice'):
            dts += [Level.Tags.Ice, Level.Tags.Holy]
        if u:
            dmg = self.get_stat('damage')
            for dt in dts:
                u.deal_damage(dmg, dt, self)
            if self.get_stat('mash'):
                u.apply_buff(Level.Silence(), 3)
        if not u.is_alive() and self.get_stat('flash'):
            self.owner.level.queue_spell(self.refr())

    def refr(self):
        self.owner.quick_cast_used = False
        yield

class RainPlus(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Flashing Sky Bow Array"
        self.level = 6
        self.description = "The first time you cast Myriad Arrows each realm, also cast it on all units in its range for free."
        self.owner_triggers[Level.EventOnUnitAdded] = self.refr
        self.owner_triggers[Level.EventOnSpellCast] = self.proc_rain
        self.first_cast = False

    def refr(self, evt):
        self.first_cast = False

    def proc_rain(self, evt):
        if type(evt.spell) != ArrowRain or self.first_cast:
            return
        self.first_cast = True
        sp = self.owner.get_or_make_spell(ArrowRain)
        victims = [u for u in self.owner.level.units if sp.can_cast(u.x, u.y)]
        for v in victims:
            self.owner.level.act_cast(self.owner, sp, v.x, v.y, pay_costs=False)

class ArrowRain(Level.Spell):
    def __init__(self):
        Level.Spell.__init__(self)
        self.spell_upgrades[0].spell_bonuses_pct[ArrowRain]['range'] = 50
        self.spell_upgrades[1].spell_bonuses[ArrowRain]['damage'] = 2
    def on_init(self):
        self.name = "Myriad Arrows"
        self.max_charges = 15
        self.range = 11
        self.can_target_empty = False
        self.tags = [Level.Tags.Holy, Level.Tags.Sorcery]
        self.level = 1
        self.damage = 3
        self.asset = ["ATGMPack", "icons", "myriad_arrows"]

        self.upgrades['requires_los'] = (-1, 5, "Keen Veiled Glow Barrage", "Myriad Arrows no longer requires line of sight to cast, and gains a 40% chance to not consume a charge when targeting units not in LOS.")
        self.upgrades['void'] = (1, 5, "Perfect Void Quiver Art", "Also deal [arcane] damage, and deal 1 extra hit for every 3 remaining charges, rounded down.")
        self.upgrades['quick_cast'] = (1, 4, "Nimble Binding Ray Arrow", "Casting Myriad Arrows only takes half of your turn.\nIf Myriad Arrows is quick casted, stun the target for 4 turns.")
        self.add_upgrade(RainPlus())

    def get_description(self):
        return (
            "Deal [{damage}_holy_damage:holy] 5 times."
        ).format(**self.fmt_dict())

    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        num_hits = 5
        if self.get_stat('void'):
            num_hits += self.cur_charges // 3
        if u:
            for _ in range(num_hits):
                u.deal_damage(self.get_stat('damage'), Level.Tags.Holy, self)
                if self.get_stat('void'):
                    u.deal_damage(self.get_stat('damage'), Level.Tags.Arcane, self)
                if self.get_stat('quick_cast') and self.caster.quick_cast_used:
                    u.apply_buff(Level.Stun(), 4)
        if random.random() < .4 and not self.get_stat('requires_los') and u not in self.caster.level.get_units_in_los(self.caster):
            self.cur_charges = min(self.cur_charges+1, self.get_stat('max_charges'))

class ReminderCurse(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Curse of the Reminder"
        self.color = Level.Tags.Holy.color
        self.buff_type = Level.BUFF_TYPE_CURSE
        self.owner_triggers[Level.EventOnDamaged] = self.redeal

    def redeal(self, evt):
        if type(evt.source) != Level.Buff or evt.damage <= 0 or type(evt.source) == ReminderCurse:
            return
        if evt.source.buff_type != Level.BUFF_TYPE_CURSE:
            return
        dmg = max(evt.damage // 3, 1)
        self.owner.deal_damage(dmg, Level.Tags.Holy, self)

class Reminder(Level.Spell):

    def on_init(self):
        self.name = "Reminder of Mortality"
        self.tags = [Level.Tags.Holy, Level.Tags.Enchantment]
        self.level = 3
        self.max_charges = 6
        self.requires_los = self.can_target_empty = False
        self.range = 9

        self.asset = ["ATGMPack", "Icons", "mortal_reminder"]

        self.upgrades['helping'] = (1, 3, "Helping Hand", "Any buffs on an ally are extended by 5 turns.")
        self.upgrades['notnice'] = (1, 4, "Unfriendly Reminder", "Enemies gain Curse of the Reminder for [7_turns:duration], which redeals one-third of damage from debuffs other than itself as [holy] damage.")
        self.upgrades['quick_cast'] = (1, 3, "Fast Alarm", "Casting Reminder of Mortality only takes half of your turn.")


    def get_description(self):
        return (
            "Target gains [living] and loses [undead], then loses 1 reincarnation if it is an enemy that does not gain clarity."
        ).format(**self.fmt_dict())

    def cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        if Level.Tags.Living not in u.tags:
            u.tags.append(Level.Tags.Living)
        if Level.Tags.Undead in u.tags:
            u.tags.remove(Level.Tags.Undead)
        if not Level.are_hostile(self.caster, u) and self.get_stat('helping'):
            for b in u.buffs:
                if u.buff_type == Level.BUFF_TYPE_BLESS and b.turns_left > 0:
                    b.turns_left += 5
        if Level.are_hostile(u, self.caster):
            if not u.gets_clarity:
                b = u.get_buff(CommonContent.ReincarnationBuff)
                if not b:
                    return
                if b.lives == 1:
                    u.remove_buff(b)
                else:
                    b.lives -= 1
            if self.get_stat('notnice'):
                u.apply_buff(ReminderCurse(), 7+self.get_stat('duration'))
        yield

class Unseal(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Unseal Harbingers"
        self.level = 6
        self.description = "For each 33 [fire], [lightning], or [physical] damage dealt by this spell, summon a warlock.\nThe warlock may gain additional abilities and resistances based on the most recent damage type this spell dealt."
        self.global_triggers[Level.EventOnDamaged] = self.proc
        self.ct = 0
        self.last_dtype = None
        self.table = {
            Level.Tags.Fire: BossSpawns.Flametouched,
            Level.Tags.Lightning: BossSpawns.Stormtouched,
            Level.Tags.Physical: BossSpawns.Metallic
        }

    def proc(self, evt):
        if type(evt.source) != TrumpetHail:
            return
        if evt.damage_type not in [Level.Tags.Physical, Level.Tags.Lightning, Level.Tags.Fire]:
            return
        self.ct += evt.damage
        self.last_dtype = evt.damage_type
        while self.ct >= 33:
            w = Monsters.Warlock()
            s = self.owner.get_or_make_spell(TrumpetHail)
            CommonContent.apply_minion_bonuses(s, w)
            BossSpawns.apply_modifier(self.table[self.last_dtype], w)
            self.summon(w, self.owner, radius=99)
            self.ct -= 33


class TrumpetHail(Level.Spell):

    def on_init(self):
        self.name = "Revelation of Hailfire"
        self.tags = [Level.Tags.Holy, Level.Tags.Ice, Level.Tags.Sorcery, Level.Tags.Chaos]
        self.level = 3
        self.max_charges = 13
        self.range = 10
        self.can_target_empty = False

        self.upgrades['frost'] = (1, 3, "Halting Hailstorm", "Each [ice] hit freezes the target for 2 turns if it isn't already frozen.")
        self.upgrades['venom'] = (1, 3, "Wormwood", "Revelation of Hailfire can also deal [arcane] or [poison] hits, both of which add 1 turn of [poison] to the target.\nThis will extend existing [poison] on the target.")
        self.upgrades['angels'] = (1, 5, "The First Omen", "Each [holy] hit against a unit has a 15% chance to summon a seraph near you, which benefits from bonuses to Call Seraph where applicable.")
        self.add_upgrade(Unseal())

        self.asset = ["ATGMPack", "icons", "hailfire_rev"]

    def get_extra_examine_tooltips(self):
        w = Monsters.Warlock()
        CommonContent.apply_minion_bonuses(self, w)
        return self.spell_upgrades + [w]

    def get_description(self):
        return (
            "Target randomly takes a fixed 1 [holy], [ice], [fire], [lightning], or [physical] damage 33 times."
        ).format(**self.fmt_dict())

    def cast(self, x, y):
        num_hits = 33
        u = self.caster.level.get_unit_at(x, y)
        dts = [Level.Tags.Holy, Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Physical, Level.Tags.Lightning]
        wormwood_dts = [Level.Tags.Arcane, Level.Tags.Poison]
        if self.get_stat('venom'):
            dts.extend(wormwood_dts)
        if u:
            for _ in range(num_hits):
                dt = random.choice(dts)
                self.caster.level.deal_damage(x, y, 1, dt, self)
                if dt == Level.Tags.Ice and u and not u.has_buff(CommonContent.FrozenBuff) and self.get_stat('frost'):
                    u.apply_buff(CommonContent.FrozenBuff(), 2)
                elif dt in wormwood_dts and u:
                    if(b := u.get_buff(CommonContent.Poison)):
                        b.turns_left += 1
                    else:
                        u.apply_buff(CommonContent.Poison(), 1)
                elif dt == Level.Tags.Holy and self.get_stat('angels') and random.random() < 0.15 and u:
                    ang = self.caster.get_or_make_spell(Spells.SummonSeraphim).make_angel()
                    self.summon(ang, self.caster)
                yield


class MegaDoom(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Arrival of the End"
        self.level = 8
        self.description = "Any unit summoned by Doomsday Cult that dies has a 10% chance to spawn a random fiend, and a 3% chance to spawn a random rider.\nThese are treated as summons from this spell."
        self.global_triggers[Level.EventOnDeath] = self.proc

    def proc(self, evt):
        s = self.owner.get_or_make_spell(DoomTroupe)
        if Level.are_hostile(evt.unit, self.owner) or type(evt.unit.source) != DoomTroupeBuff:
            return
        if random.random() < .1:
            valids = [m[0] for m in Monsters.spawn_options if "fiend" in m[0]().name.lower() and Level.Tags.Living not in m[0]().tags]
            f = BossSpawns.apply_modifier(BossSpawns.Immortal, random.choice(valids)())
            s.summon(f, evt.unit, radius=99)
        if random.random() < .03:
            valids = [RareMonsters.BlackRider, RareMonsters.RedRider, RareMonsters.PaleRider, RareMonsters.WhiteRider]
            r = random.choice(valids)()
            s.summon(r, evt.unit, radius=99)


class DoomTroupeBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnDeath] = self.cult
        self.global_triggers[Level.EventOnUnitAdded] = self.cull_perm
        self.color = Level.Tags.Chaos.color
        self.name = "Doomsday Cult"
        self.global_bonuses_pct['minion_damage'] = -20 
        self.global_bonuses_pct['minion_range'] = -50 
        self.tag_bonuses_pct[Level.Tags.Chaos]['minion_damage'] = 20
        self.tag_bonuses_pct[Level.Tags.Chaos]['minion_range'] = 50
        self.opts = [Monsters.Cultist, Variants.CultistLeader, Variants.CultistChosen]
        self.weights = [10, 1, 5]
        if spell.get_stat('immort'):
            self.weights.append(10)
            self.opts.append(Monsters.FalseProphet)

    def cult(self, evt):
        if Level.are_hostile(evt.unit, self.owner) or evt.unit == self.owner or evt.unit.source == self or evt.unit.turns_to_death != 0:
            return
        else:
            ct = evt.unit.max_hp
            while ct > 1:
                m = random.choices(self.opts, self.weights)[0]()
                m = BossSpawns.apply_modifier(BossSpawns.Chaostouched, m)
                CommonContent.apply_minion_bonuses(self.spell, m)
                self.summon(m, evt.unit, radius=99)
                m.turns_to_death = None
                ct -= m.max_hp

    def cull_perm(self, evt):
        if Level.are_hostile(evt.unit, self.owner) or evt.unit == self.owner or evt.unit.source == self or evt.unit.source == self.spell:
            return
        if evt.unit.turns_to_death == None or evt.unit.turns_to_death > 7:
            evt.unit.turns_to_death = random.randrange(4, 7)

class DoomTroupe(Level.Spell):
    def on_init(self):
        self.name = "Doomsday Cult"
        self.max_charges = 3
        self.tags = [Level.Tags.Enchantment, Level.Tags.Conjuration, Level.Tags.Dark, Level.Tags.Chaos]
        self.range = 0
        self.level = 5
        self.duration = 16

        ex = BossSpawns.apply_modifier(BossSpawns.Chaostouched, Monsters.Cultist())
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage
        self.minion_range = ex.spells[0].range

        self.asset = ["ATGMPack", "icons", "doomsday_cult"]

        self.upgrades['immort'] = (1, 4, "Eternity Heretics", "Infernal false prophets can appear as well.")
        self.add_upgrade(MegaDoom())
        self.upgrades['scale'] = (1, 6, "Cult of the Serpent-King", "Summon an infernal Slazephan when you cast this spell.")

    def get_extra_examine_tooltips(self):
        return self.spell_upgrades[:2] + [self.slazzy()] + self.spell_upgrades[2:]

    def get_description(self):
        return (
            "For [{duration}_turns:duration], whenever a temporary ally's duration expires, a variety of infernal cultists appear based on its max HP.\n"
            "While this effect is active, spells that are not [chaos] lose [minion_damage:minion_damage] and [minion_range:minion_range].\n"
            "When a minion from a source other than this spell is summoned, its duration will be set to a random number between 4 and 7 turns if it does not already have a duration or its duration is higher than 7.\n"
            "This effect lasts [{duration}_turns:duration]."
        ).format(**self.fmt_dict())
    
    def slazzy(self):
        m = RareMonsters.SerpentPhilosopher()
        CommonContent.apply_minion_bonuses(self, m)
        BossSpawns.apply_modifier(BossSpawns.Chaostouched, m)
        return m
    
    def cast_instant(self, x, y):
        self.caster.apply_buff(DoomTroupeBuff(self), self.get_stat('duration'))
        if self.get_stat('scale'):
            m = self.slazzy()
            self.summon(m, Level.Point(x,y), radius=99)

class Wabbagate(Level.Spell):
    def on_init(self):
        self.name = "Wabba Spawner"
        self.max_charges = 4
        self.level = 3
        self.tags = [Level.Tags.Chaos, Level.Tags.Conjuration]
        self.range = 6

        self.minion_health = 40

        self.must_target_walkable = True

        self.asset = ["ATGMPack", "icons", "wabbagate"]

        self.upgrades['greater'] = (3, 5, "Greater Spawners", "Spawn tier 7 monsters instead.")
        self.upgrades['sigil'] = (1, 3, "Sigilist", "On casting Wabba Spawner, also summon a spawner from a random sigil you own.")
        self.upgrades['liches'] = (1, 5, "Darkspawn", "Wabba Spawner summons [lich:dark] spawners.")
        self.upgrades['rapid'] = (1, 4, "Swarm Gate", "Gate spawn cooldown is fixed at 4 turns.")

    def get_description(self):
        return (
            "Summon a spawner on target tile, which will spawn a random tier 4 monster."
        )
    
    def spawn(self, func):
        m = func()
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def cast_instant(self, x, y):
        tier = 4 + self.get_stat('greater')
        valids = [m[0] for m in Monsters.spawn_options if m[1] == tier]
        tgt = random.choice(valids)
        g = CommonContent.MonsterSpawner(lambda: self.spawn(tgt))
        if self.get_stat('liches'):
            g = CommonContent.MonsterSpawner(lambda: BossSpawns.apply_modifier(BossSpawns.Lich, self.spawn(tgt)))
        if self.get_stat('rapid'):
            g.spells[0].cool_down = 4
        CommonContent.apply_minion_bonuses(self, g)
        self.summon(g, Level.Point(x, y))
        if self.get_stat('sigil'):
            equs = [e for e in self.caster.trinkets if type(e) == Equipment.PetSigil]
            if equs:
                m = CommonContent.MonsterSpawner(random.choice(equs).spawn_fn)
                self.summon(m, Level.Point(x, y), radius=99)


class BoilPlagueBuff(Level.Buff):
    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.spell = spell
        self.name = "Boils"
        self.color = Level.Tags.Nature.color
        self.BUFF_TYPE = Level.BUFF_TYPE_CURSE
        self.owner_triggers[Level.EventOnDeath] = self.boom
    
    def try_infect(self, u, chance):
        if self.spell.can_spread(u) and random.random() < chance and not u.has_buff(BoilPlagueBuff):
            if u.is_player_controlled:
                if not self.spell.get_stat('exp'):
                    return
                else:
                    b = BoilPlagueBuff(self.spell)
                    b.resists[Level.Tags.Poison] = 100
                    b.resists[Level.Tags.Holy] = 100
                    b.owner_triggers[Level.EventOnDamaged] = CommonContent.RetaliationBuff(5, Level.Tags.Holy)
                    b.buff_type = Level.BUFF_TYPE_BLESS
                    u.apply_buff(b, 33)
            else:
                u.apply_buff(BoilPlagueBuff(self.spell))

    def boom(self, evt):
        self.owner.level.queue_spell(self.aoe())

    def aoe(self):
        boomrad = self.spell.get_stat('radius')+1
        for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, boomrad):
            u = self.owner.level.get_unit_at(p.x, p.y)
            self.owner.level.deal_damage(p.x, p.y, self.spell.get_stat('damage'), random.choice([Level.Tags.Holy, Level.Tags.Poison]), self)
            if u:
                self.try_infect(u, .3)
            yield

    def on_advance(self):
        self.owner.level.queue_spell(self.do_effect())

    def do_effect(self):
        pots = [u for u in self.owner.level.get_units_in_ball(self.owner, self.spell.get_stat('radius')) if u != self.owner]
        if not pots:
            return
        nt = self.spell.get_stat('num_targets')
        victims = random.choices(pots, k=nt) if len(pots) < nt else random.sample(pots, k=nt)
        for v in victims:
            d = 5 if not v.is_player_controlled else 1
            dtype = random.choice([Level.Tags.Holy, Level.Tags.Poison])
            v.deal_damage(d, dtype, self.spell)
            self.try_infect(v, .13)
            self.owner.level.show_path_effect(self.owner, v, dtype, minor=True)
            if self.spell.get_stat('ash') and not v.is_player_controlled:
                v.deal_damage(3, Level.Tags.Fire, self.spell)
                self.try_infect(v, .13)
            yield


class BoilPlague(Level.Spell):
    def on_init(self):
        self.name = "Epidemic of Boils"
        self.max_charges = 3
        self.tags = [Level.Tags.Enchantment, Level.Tags.Holy, Level.Tags.Nature]
        self.range = 5
        self.level = 6
        self.radius = 4
        self.num_targets = 7
        self.can_target_empty = False
        self.asset = ["ATGMPack", "icons", "boil_epidemic"]
        self.damage = 16

        self.upgrades['univ'] = (1, 4, "Evolved Epidemic", "Any unit type can now be infected with Boils.")
        self.upgrades['ash'] = (1, 4, "Ash Boils", "Bursts from Boils also deal a fixed 3 [fire] damage to units except the Wizard, which adds another separate 13% chance to infect the target.")
        self.upgrades['exp'] = (1, 6, "Self-Experimentation", "The Wizard can now be infected with Boils, which lasts 33 turns.\nThis version of Boils grants 100 [holy] and [poison] resistance and retaliation dealing a fixed 5 [holy] damage, and is considered a buff.")

    def can_cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return False
        return Level.Spell.can_cast(self, x, y) and self.can_spread(u)

    def can_spread(self, u):
        if self.get_stat('univ'):
            return True
        return any(t in [Level.Tags.Demon, Level.Tags.Nature, Level.Tags.Living] for t in u.tags)
    
    def fmt_dict(self):
        d = Level.Spell.fmt_dict(self)
        d['boil_rad'] = d['radius']+1
        return d

    def get_description(self):
        return (
            "Infect target unit with Boils, which sends out [{num_targets}:num_targets] bursts of sacred bacterial matter towards units in [{radius}_tiles:radius] each turn. Bursts will try to target unique units, if possible.\n"
            "Each burst deals a fixed 5 [holy] or [poison] damage to its target (1 if the Wizard), and has a 13% chance to infect the hit unit with Boils.\n"
            "When a unit with Boils dies, it explodes, dealing [{damage}:damage] [holy] or [poison] damage to all units in a [{boil_rad}-tile_radius:radius].\n"
            "The explosion has a 30% chance to infect hit units.\n"
            "Only [living], [demon], and [nature] units can be infected with Boils, and the Wizard cannot be infected."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if u:
            u.apply_buff(BoilPlagueBuff(self))

class AuroraRadPlus(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.spell_bonuses[AuroraRing]['radius'] = 1
        self.stack_type = Level.STACK_INTENSITY
        self.color = Level.Tags.Fire.color
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.name = "Storm Spread"

class AuroraRing(Level.Spell):
    def on_init(self):
        self.name = "Aurora Tornado"
        self.max_charges = 6
        self.level = 4
        self.tags = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Sorcery]
        self.range = 0
        self.damage = 8
        self.radius = 5

        self.asset = ["ATGMPack", "icons", "aurora_tornado"]

        self.upgrades['chaotic'] = (1, 5, "Chaos Tornado", "Before each [ice] hit from this spell, deal [lightning] or [physical] damage randomly.")
        self.upgrades['frost'] = (1, 3, "Frosty Finish", "Add an additional [ice] hit dealing a fixed 10 damage at the end of the spell, which inflicts 4 turns of [frozen:ice].")
        self.upgrades['growth'] = (1, 4, "Storm Spread", "On a kill, Aurora Tornado gains +1 radius for 3 turns.")

    def get_impacted_tiles(self, x, y):
        points = self.caster.level.get_points_in_ball(self.caster.x, self.caster.y, self.get_stat('radius'))
        return [p for p in points if p != Level.Point(self.caster.x, self.caster.y) and Level.distance(self.caster, p) >= self.get_stat('radius') - 1]
    
    def get_description(self):
        return (
            "All units in a [{radius}-tile_ring:radius] take [{damage}_ice_damage:ice] and are [frozen:ice] for 1 turn, then take a fixed 1 fire damage.\n"
            "This process repeats 3 times."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        for t in self.get_impacted_tiles(x, y):
            u = self.caster.level.get_unit_at(t.x, t.y)
            for _ in range(3):
                if self.get_stat('chaotic'):
                    self.caster.level.deal_damage(t.x, t.y, self.get_stat('damage'), random.choice([Level.Tags.Physical, Level.Tags.Lightning]), self)
                self.caster.level.deal_damage(t.x, t.y, self.get_stat('damage'), Level.Tags.Ice, self)
                if u and u.is_alive():
                    u.apply_buff(CommonContent.FrozenBuff(), 1)
                self.caster.level.deal_damage(t.x, t.y, 1, Level.Tags.Fire, self)
            if self.get_stat('frost'):
                self.caster.level.deal_damage(t.x, t.y, 10, Level.Tags.Ice, self)
                if u:
                    u.apply_buff(CommonContent.FrozenBuff(), 4)
            if u and not u.is_alive() and self.get_stat('growth'):
                self.caster.apply_buff(AuroraRadPlus(), 3)


class StatShuffle(Level.Spell):
    def on_init(self):
        self.name = "Mirror Multiverse"
        self.max_charges = 1
        self.level = 6
        self.tags = [Level.Tags.Arcane, Level.Tags.Enchantment]
        self.range = 0

        self.asset = ["ATGMPack", "icons", "mirror_multiverse"]

        self.upgrades['global'] = (1, 3, "Breadth of Reflection", "Mirror Multiverse now affects all units except the Wizard.")
        self.upgrades['cull'] = (1, 5, "Rigged Multiverse", "For the purposes of shuffling, the enemies with the highest max HP are treated as having a max HP of 1.")
        self.upgrades['refl'] = (1, 3, "Perfect Mirror", "Summon a friendly copy of the enemy unit with the lowest max HP before shuffling.\nThe clone does not get any non-passive buffs that enemy has.")
    
    def get_description(self):
        return (
            "Randomly shuffle the max HP of all enemies, then sets all enemies to max HP."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        victims = [u for u in self.caster.level.units if Level.are_hostile(self.caster, u) or (not u.is_player_controlled and self.get_stat('global'))]
        random.shuffle(victims)
        print(len(victims))
        to_call = min(victims, key=lambda x: x.max_hp)
        if self.get_stat('refl'):
            clone = Level.Unit()
            for k in vars(to_call).keys():
                setattr(clone, k, getattr(to_call, k))
            clone.spells = []
            clone.buffs = []
            for s in to_call.spells:
                clone.spells.append(s)
                s.caster = s.owner = clone
            self.summon(clone, Level.Point(x,y))
            for b in to_call.buffs:
                if b.buff_type == Level.BUFF_TYPE_PASSIVE:
                    clone.apply_buff(type(b)(), b.turns_left)
            clone.Anim = None
        hps = [v.max_hp for v in victims]
        if self.get_stat('cull'):
            m = max(hps)
            for j in range(len(hps)):
                if hps[j] == m:
                    hps[j] = 1
        for i in range(len(victims)):
            victims[i].max_hp = victims[i].cur_hp = hps[i]


class Grail(Level.Spell):
    def on_init(self):
        self.name = "Sip of the Grail"
        self.max_charges = 3
        self.level = 3
        self.tags = [Level.Tags.Metallic, Level.Tags.Holy, Level.Tags.Blood, Level.Tags.Enchantment]
        self.range = 0
        self.hp_cost = 7

        self.asset = ["ATGMPack", "icons", "holy_grail"]
        self.phoenix_counter = 0

        self.upgrades['compound'] = (1, 7, "Compounding Health", "Targets instead gain 30% of their current maximum HP and are healed for that amount.")
        self.upgrades['ash'] = (1, 5, "Ash Grail", "For every 250 HP healed by this spell, summon a phoenix.\n")
        self.upgrades['aurum'] = (1, 4, "Radiant Blessing", "Gain an aura dealing a fixed 3 [holy] damage in a 5 tile radius for 13 turns whenever you cast this spell.")
    
    def get_description(self):
        return (
            "All allies except the caster gain [3_max_HP:heal] and are then healed for that amount."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        candidates = [u for u in self.caster.level.units if not Level.are_hostile(self.caster, u) and u != self.caster]
        for c in candidates:
            amt = 3
            if self.get_stat('compound'):
                amt = math.floor(c.max_hp*.3)
            c.max_hp += amt
            d = c.deal_damage(-amt, Level.Tags.Heal, self)
            self.phoenix_counter += abs(d)
        if self.get_stat('ash'):
            while self.phoenix_counter >= 250:
                m = Monsters.Phoenix()
                CommonContent.apply_minion_bonuses(self, m)
                self.summon(m, self.caster, radius=99)
                self.phoenix_counter -= 250
        if self.get_stat('aurum'):
            b = CommonContent.DamageAuraBuff(damage=3, damage_type=Level.Tags.Holy, radius=5)
            b.name = "Grail Aura"
            b.color = Level.Tags.Holy.color
            self.caster.apply_buff(b, 13)


class BondRiteBuff(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.color = Level.Tags.Slime.color
        self.name = "Binding Rite"
        self.owner_triggers[Level.EventOnDeath] = self.on_death

    def on_death(self, evt):
        u = self.spell.fleshslime()
        if self.spell.get_stat('star'):
            u = self.spell.fleshslime_arc()
        self.spell.summon(u, self.owner)

class PurposeIdolBuff(Level.Buff):

    def __init__(self, spell):
        self.spell = spell
        Level.Buff.__init__(self)
        self.name = "Ultimate Purpose"
        self.color = Level.Tags.Slime.color

    def on_advance(self):
        victims = [u for u in self.owner.level.units if Level.are_hostile(self.owner, u) and not u.has_buff(BondRiteBuff)]
        if not victims:
            return
        v = random.choice(victims)
        self.owner.level.show_path_effect(self.owner, v, Level.Tags.Blood, minor=True)
        v.apply_buff(BondRiteBuff(self.spell))

    def get_tooltip(self):
        return "Curses enemies, making them spawn fleshbound slimes on death."
    
class PatronLord(Upgrades.Upgrade):
    def on_init(self):
        self.name = "Plea to the Patron"
        self.level = 6
        self.global_triggers[Level.EventOnUnitAdded] = self.call_patron
        self.description = "For every 66 units summoned by this spell, summon the Slimebond Patron near the most recently summoned one."
        self.num_slimes = 0
    
    def call_patron(self, evt):
        sp = self.owner.get_or_make_spell(Slimecult)
        if not isinstance(evt.unit.source, Slimecult):
            return
        self.num_slimes += 1
        while self.num_slimes >= 66:
            self.summon(sp.patron(), self.owner)
            self.num_slimes -= 66

class PatronBoon(Level.Buff):
    def __init__(self):
        Level.Buff.__init__(self)
        self.name = "Prashrag's Flesh"
        self.color = Level.Tags.Blood.color
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.resists[Level.Tags.Dark] = 100
    
    def on_advance(self):
        self.owner.max_hp += 3
        self.owner.cur_hp += 3

    def on_attempt_apply(self, owner):
        if Level.Tags.Slime not in owner.tags or owner.is_player_controlled:
            return False
        return True

class Slimecult(Level.Spell):
    def on_init(self):
        self.name = "Sect of the Slimebound"
        self.max_charges = 2
        self.level = 5
        self.tags = [Level.Tags.Blood, Level.Tags.Dark, Level.Tags.Conjuration]
        self.range = 7
        self.hp_cost = 20

        self.asset = ["ATGMPack", "icons", "purpose_cult"]
        self.must_target_walkable = True

        ex = Variants.CultistChosen()
        self.minion_health = ex.max_hp
        self.minion_damage = ex.spells[0].damage
        self.minion_range = ex.spells[0].range
        self.num_summons = 8

        self.upgrades['splitters'] = (1, 4, "Zenith of Devotion", "This spell no longer summons an idol, but the cultists are now [slimes:slime] and can split like them.\nAdditionally, their Pain is replaced with Siphon Flesh, which has no self-damage, melts walls, and drains life.")
        self.upgrades['star'] = (1, 4, "Astral Flesh", "The idol becomes [fae:arcane] and summons void slimes instead.")
        self.add_upgrade(PatronLord())

    def get_extra_examine_tooltips(self):
        t = copy.copy(self.spell_upgrades)
        t.insert(0, self.idol())
        t.insert(0, self.cultist())
        t.insert(0, self.fleshslime())
        t.insert(5, self.fleshslime_arc())
        t.append(self.patron())
        return t
    
    def get_description(self):
        return (
            "[{num_summons}:num_summons] [fleshbound:blood] cultist chosen appear, surrounding a Slimebond Idol.\n"
            "The slimebond idol curses enemies, making them spawn [fleshbound:blood] slimes on death.\n"
            "On summon, the slimes' max HP is rounded to the nearest multiple of 10."
        ).format(**self.fmt_dict())
    
    def cultist(self):
        m = BossSpawns.apply_modifier(BossSpawns.Hivemind, Variants.CultistChosen())
        if self.get_stat('splitters'):
            atk = m.spells[0]
            m.buffs.append(Monsters.SlimeBuff(self.cultist, name="chosen ones"))
            m.tags.append(Level.Tags.Slime)
            siphon = CommonContent.SimpleRangedAttack(damage=atk.damage, damage_type=Level.Tags.Dark, range=atk.range, beam=True, melt=True, drain=True)
            siphon.name = "Siphon Flesh"
            m.spells[0] = siphon
            m.name = "Prashrag's Chosen"
        CommonContent.apply_minion_bonuses(self, m)

        return m
    
    def idol(self):
        m = Monsters.Idol()
        m.asset = ["ATGMPack", "units", "purpose_idol"]
        m.name = "Slimebond Idol"
        m.buffs.append(PurposeIdolBuff(self))
        CommonContent.apply_minion_bonuses(self, m)
        if self.get_stat('star'):
            BossSpawns.apply_modifier(BossSpawns.Faetouched, m)
        return m
    
    def fleshslime(self):
        m = Monsters.GreenSlime()
        m = BossSpawns.apply_modifier(BossSpawns.Hivemind, m)
        CommonContent.apply_minion_bonuses(self, m)
        m.max_hp = math.ceil(m.max_hp/10)*10
        return m
    
    def fleshslime_arc(self):
        m = Monsters.VoidSlime()
        m = BossSpawns.apply_modifier(BossSpawns.Hivemind, m)
        CommonContent.apply_minion_bonuses(self, m)
        m.max_hp = math.ceil(m.max_hp/10)*10
        return m
    
    def patron(self):
        m = Monsters.RedSlime()
        for b in [BossSpawns.Immortal, BossSpawns.Flametouched, BossSpawns.Hivemind]:
            m = BossSpawns.apply_modifier(b, m)
        m.name = "Prashrag, the Slimebond Patron"
        m.spells[0].damage *= 3
        boon = CommonContent.SimpleCurse(PatronBoon, 5)
        boon.name = "Share Flesh"
        boon.cool_down = 10
        boon.description = "A [slime] ally gains 100 [dark] resist and regenerates 3 current and maximum HP each turn for 5 turns."
        boon.can_cast_old = boon.can_cast
        boon.can_cast = lambda x, y: boon.can_cast_old(x, y) and PatronBoon().on_attempt_apply(boon.caster.level.get_unit_at(x, y))
        m.spells.insert(0, boon)
        CommonContent.apply_minion_bonuses(self, m)
        m.max_hp = math.ceil(m.max_hp/10)*30
        m.buffs[0].spawner = self.patron
        return m
    
    def cast_instant(self, x, y):
        if not self.get_stat('splitters'):
            self.summon(self.idol(), Level.Point(x, y))
        for _ in range(self.get_stat('num_summons')):
            self.summon(self.cultist(), Level.Point(x, y), radius=99)
        

#Spells.all_player_spell_constructors.clear()

mod_spells = [
    DustBowl, 
    Slimeteor, 
    MedusaForm, 
    InsectPlague, 
    SlowTaxSpell, 
    FogChokeSpell, 
    Treeflame, 
    ZPulse, 
    Bardchant, 
    TroubleForm, 
    GlassSlime, 
    DracoRitual, 
    MindSuck, 
    LightningSlime, 
    WordWrath, 
    SandDragon, 
    GlassBolt, 
    HoardSummon, 
    GiantAxe, 
    SplitScreen, 
    SuperThief, 
    BigBag, 
    BloodCopy, 
    ShrinkMinions, 
    SenselessCast, 
    SaltPillar, 
    RayPierceSpell, 
    DoomTroupe, 
    IceShiv, 
    RazorScales, 
    BloodElectro, 
    WeirdSpider, 
    Knife,
    ArrowRain, 
    Reminder,
    TrumpetHail,
    Wabbagate,
    BoilPlague,
    AuroraRing,
    StatShuffle,
    Grail,
    Slimecult
]

Spells.all_player_spell_constructors.extend(mod_spells)