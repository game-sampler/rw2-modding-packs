import Spells
import Upgrades
import Level
import CommonContent
import Variants
import RareMonsters
import BossSpawns
import Monsters  
import Upgrades
import text
import os, math, random

class OrnamentGlassify(CommonContent.GlassPetrifyBuff):
    def __init__(self, origspell):
        self.origspell = origspell
        CommonContent.GlassPetrifyBuff.__init__(self)
    def on_applied(self, owner):
        if self.origspell.get_stat('phosphoric'):
            self.resists[Level.Tags.Fire] = 0
            self.resists[Level.Tags.Ice] = 0
            self.resists[Level.Tags.Lightning] = 0
            self.name = "Acid Glassed"
    def on_attempt_advance(self):
        if self.origspell.get_stat('phosphoric'):
            self.owner.level.deal_damage(self.owner.x, self.owner.y, 8, Level.Tags.Arcane, self)
        return False

class Ornament(Level.Spell):
    def on_init(self):
        self.level = 3
        self.tags = [Level.Tags.Arcane, Level.Tags.Sorcery]
        self.name = "Ornament Shatter"
        self.damage = 15
        self.range = 8
        self.radius = 3
        self.duration = 5
        self.max_charges = 9

        self.asset = ["HolidayPack2", "Ornament"]

        self.upgrades['phosphoric'] = (1, 5, "Glass Melt", "Ornaments inflict a special form of glassification that grants no bonuses to the target's [fire], [ice] or [lightning] resistances and deals 8 [arcane] damage to them every turn.")
        self.upgrades['metallize'] = (1, 5, "Tungsten Ornaments", "Ornaments deal [physical] damage in their radius, and double at the center tile.")
        self.upgrades['shardshot'] = (1, 6, "Shardshot", "Ornaments do not directly impact the targeted tile, but instead split into 4 shards that home in on random enemies in a [7_tile_burst:radius], casting this spell on them but with halved damage and radius.\nIf there are 4 or less enemies in range, the shards target all enemies in the burst.")

    def get_description(self):
        return (
                "Break a magic ornament on target tile, dealing [{damage}_arcane_damage:arcane] in a [{radius}_tile_burst:radius].\n"
                "The ornament inflicts [glassify] on units in its radius for [{duration}_turns:duration].\n"
                + text.glassify_desc
                ).format(**self.fmt_dict())
    def get_impacted_tiles(self, x, y):
        if not self.get_stat('shardshot'):
            return [p for stage in CommonContent.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius')) for p in stage]
        else:
            points = []
            units = self.get_shardshot_targets(x, y)
            for u in units:
                plist = [p for stage in CommonContent.Burst(self.caster.level, Level.Point(u.x, u.y), self.get_stat('radius')//2) for p in stage]
                points += plist
            return points

    def get_shardshot_targets(self, xpt, ypt):
        units = []
        for spread in CommonContent.Burst(self.caster.level, Level.Point(xpt, ypt), 7):
            for point in spread:
                u = self.caster.level.get_unit_at(point.x, point.y)
                if u and self.caster.level.are_hostile(self.caster, u):
                    units.append(u) 
                continue
        return units
    
    def cast(self, x, y):
        if not self.get_stat('shardshot'):
            if self.get_stat('metallize'):
                self.caster.level.deal_damage(x, y, self.get_stat('damage'), Level.Tags.Physical, self)
            for spread in CommonContent.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius')):
                for point in spread:
                    u = self.caster.level.get_unit_at(point.x, point.y)
                    if u and self.caster.level.are_hostile(self.caster, u):
                        glassify = OrnamentGlassify(self)
                        u.apply_buff(glassify, self.get_stat('duration'))
                    self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Level.Tags.Arcane, self)
                    if self.get_stat('metallize'):
                        self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Level.Tags.Physical, self)
                yield
        else:
            candidates = self.get_shardshot_targets(x, y)
            realrad = self.get_stat('radius') // 2
            realdmg = self.get_stat('damage') // 2
            targets = candidates if len(candidates) <= 4 else random.sample(candidates, 4)
            for unit in targets:
                for spread in CommonContent.Burst(self.caster.level, Level.Point(unit.x, unit.y), realrad):
                    for point in spread:
                        u = self.caster.level.get_unit_at(point.x, point.y)
                        if u and self.caster.level.are_hostile(self.caster, u):
                            glassify = OrnamentGlassify(self)
                            u.apply_buff(glassify, self.get_stat('duration'))
                        self.caster.level.deal_damage(point.x, point.y, realdmg, Level.Tags.Arcane, self)
                    yield

class BombExplode(Level.Buff):
    def __init__(self, spell):
        self.spell = spell
        self.naughty = False
        Level.Buff.__init__(self)
    
    def on_init(self):
        self.color = Level.Tags.Fire.color
        self.owner_triggers[Level.EventOnDeath] = self.on_death
        self.owner_triggers[Level.EventOnDamaged] = self.on_damage
        self.name = "Present Explosion"

    def get_tooltip(self):
        desc_str = "On death, deals %d fire damage to enemies in a %d tile burst." % (self.owner.max_hp, self.spell.get_stat('radius'))
        if self.spell.get_stat('keeps'):
            desc_str += "\nSummons 2 copies of this unit with 75% of this unit's maximum HP in random locations in 8 tiles."
        if self.spell.get_stat('naughty'):
            desc_str += "\nRespawns as a box of woe if dealt [dark] damage or damaged by a [demon] or [undead] unit."
        return desc_str
    
    def on_damage(self, evt):
        dealer = evt.source if type(evt.source) == Level.Unit else evt.source.owner
        if evt.damage_type == Level.Tags.Dark or any(t in dealer.tags for t in [Level.Tags.Demon, Level.Tags.Undead]):
            self.naughty = True

    def on_death(self, evt):
        for stage in CommonContent.Burst(self.owner.level, Level.Point(self.owner.x, self.owner.y), self.spell.get_stat('radius')):
            for point in stage:
                unit = self.owner.level.get_unit_at(point.x, point.y)
                if unit and not self.owner.level.are_hostile(unit, self.owner):
                    continue
                else:
                    self.owner.level.deal_damage(point.x, point.y, self.owner.max_hp, Level.Tags.Fire, self)

        if self.spell.get_stat('keeps'):
            new_hp = math.ceil(self.owner.max_hp*.75)
            potential = [p for stage in CommonContent.Burst(self.owner.level, Level.Point(self.owner.x, self.owner.y), 8, ignore_walls=True) for p in stage]
            potential = [t for t in potential if self.owner.level.tiles[t.x][t.y].can_walk]
            if new_hp >= 5 and len(potential) >= 2:
                spots = random.sample(potential, 2)
                for tile in spots:
                    bomb = self.spell.make_bomb()
                    bomb.max_hp = new_hp
                    if bomb.cur_hp > bomb.max_hp:
                        bomb.cur_hp = bomb.max_hp
                    self.summon(bomb, tile)

        if self.naughty and self.spell.get_stat('naughty'):
            box = self.spell.woe()
            self.spell.summon(box)


class PresentBomb(Level.Spell):
    def on_init(self):
        self.name = "Present Bomb"
        self.level = 4
        self.range = 8
        self.radius = 4
        self.minion_health = 26
        self.max_charges = 4
        self.must_target_empty = True
        self.must_target_walkable = True
        self.tags = [Level.Tags.Fire, Level.Tags.Conjuration]

        self.asset = ["HolidayPack2", "Present_Bomb"]

        self.upgrades['naughty'] = (1, 6, "Naughty List", "The present will respawn as a box of woe if it took [dark] damage or damaged by a [demon] or [undead] unit.")
        self.upgrades['keeps'] = (1, 7, "Gift That Keeps On Giving", "Presents summon 2 copies of themselves with 75% of their maximum HP when they die.\nThe new presents will be summoned in random locations within 8 tiles of the original present.\nCopies will not be summoned if their maximum HP would be lower than 5 or there are no available locations.")
        
    def get_impacted_tiles(self, x, y):
        return [Level.Point(x, y)]
    
    def get_extra_examine_tooltips(self):
        return [self.make_bomb(), self.spell_upgrades[0], self.woe(), self.spell_upgrades[1]]
    
    def woe(self):
        m = RareMonsters.BoxOfWoe()
        CommonContent.apply_minion_bonuses(self, m)
        return m
    
    def make_bomb(self):
        bomb = Level.Unit()
        bomb.name = "Exploding Present"
        bomb.stationary = True
        bomb.asset_name = os.path.join("..","..","mods","HolidayPack2","bord_present")
        bomb.max_hp = self.get_stat('minion_health')
        bomb.cur_hp = bomb.max_hp // 2
        bomb.tags = [Level.Tags.Fire, Level.Tags.Construct]
        for dtype in [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Physical]:
            bomb.resists[dtype] = -50
        bomb.resists[Level.Tags.Poison] = 0
        bomb.buffs.append(BombExplode(self))
        return bomb
    
    def get_description(self):
        return (
                "Place down an exploding present on target tile.\n"
                "The present is a stationary [fire] [construct] with [{minion_health}_HP:minion_health] and -50 [physical], [fire], and [ice] resist.\n" 
                "When the present dies, it explodes in a [{radius}_tile_burst:radius], dealing [fire] damage equal to [its_maximum_HP:damage].\n"
                ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        self.summon(self.make_bomb(), Level.Point(x, y))

class Festivities(Level.Spell):
    def on_init(self):
        self.level = 6
        self.tags = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Sorcery, Level.Tags.Conjuration]
        self.name = "Magely Festivities"
        self.max_charges = 2
        self.minion_health = 40
        self.shields = 1
        self.minion_damage = 9
        self.minion_range = 8
        self.minion_duration = 22
        self.damage = 13
        self.range = 8
        self.radius = 4
        self.minion_radius = 2
        self.stats.append('minion_radius')
        self.asset = ["HolidayPack2", "Festivities"]

        self.upgrades['servitude'] = (1, 7, "\"Elf\" Leader", "The festive wizard's attacks are replaced with the abilities of an Imp Collector.")
        self.upgrades['spirit'] = (1, 5, "Holiday Spirit", "The festive wizard becomes a lich.")

    def get_description(self):
        return (
                "Deal [{damage}:damage] [fire] and [{damage}:damage] [ice] damage in a [{radius}_tile_burst:radius].\n"
                "Summons a festive wizard at the center tile.\n"
                "The festive wizard has [{minion_health}_HP:minion_health], [{shields}_SH:shields], 100 [fire] resist, 100 [ice] resist, and 50 [dark] resist.\n"
                "The festive wizard can hurl fresh snow or hot chocolate at enemies in [{minion_range}_tiles:minion_range], dealing [{minion_damage}:minion_damage] [fire] or [ice] damage respectively in a [{minion_radius}_tile_burst:radius].\n"
                "The festive wizard vanishes after [{minion_duration}_turns:minion_duration]\n"
                ).format(**self.fmt_dict())
    
    def get_extra_examine_tooltips(self):
        return [self.make_wiz()] + self.spell_upgrades

    def get_impacted_tiles(self, x, y):
        return [p for stage in CommonContent.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius')) for p in stage]
    
    def make_wiz(self):
        wiz = Level.Unit()
        wiz.asset_name = os.path.join("..","..","mods","HolidayPack2","festive_wiz")
        wiz.name = "Festive Wizard"
        wiz.shields = self.get_stat('shields')
        wiz.max_hp = self.get_stat('minion_health')
        snow = CommonContent.SimpleRangedAttack(name="Fresh Snow", damage=self.get_stat('minion_damage'), damage_type=Level.Tags.Ice, range=self.get_stat('minion_range'), radius=self.get_stat('minion_radius'))
        cocoa = CommonContent.SimpleRangedAttack(name="Hot Chocolate", damage=self.get_stat('minion_damage'), damage_type=Level.Tags.Fire, range=self.get_stat('minion_range'), radius=self.get_stat('minion_radius'))
        wiz.spells = [snow, cocoa]
        for s in wiz.spells:
            s.cool_down = 2
        wiz.turns_to_death = self.get_stat('minion_duration')
        wiz.resists[Level.Tags.Ice] = 100
        wiz.resists[Level.Tags.Fire] = 100
        wiz.resists[Level.Tags.Dark] = 50
        wiz.tags = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Living]
        if self.get_stat('spirit'):
            BossSpawns.apply_modifier(BossSpawns.Lich, wiz)
        if self.get_stat('servitude'):
            wiz.spells = RareMonsters.ImpCollector().spells
        return wiz
    
    def cast(self, x, y):
        dtypes = [Level.Tags.Fire, Level.Tags.Ice]
        for spread in CommonContent.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius')):
            for point in spread:
                for dtype in dtypes:
                    self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), dtype, self)
            yield
        self.summon(self.make_wiz(), Level.Point(x, y))
        yield

class SecretSanta(Level.Spell):
    def on_init(self):
        self.level = 6
        self.tags = [Level.Tags.Sorcery, Level.Tags.Enchantment]
        self.name = "Secret Santa"
        self.damage = 22
        self.range = 9
        self.radius = 4
        self.duration = 9
        self.max_charges = 3
        self.requires_los = False
        self.magnitude = 7
        self.stats.append('magnitude')

        self.upgrades['magnitude'] = (4, 4, "Magnitude", "Attribute bonuses from this spell are strengthened.")
        self.upgrades['radius'] = (2, 3)
        self.upgrades['max_charges'] = (3, 2)

        self.asset = ["HolidayPack2", "Secret"]

    def get_targets(self, x, y):
        units = []
        for spread in CommonContent.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius'), ignore_walls=True):
            for point in spread:
                u = self.caster.level.get_unit_at(point.x, point.y)
                if u:
                    units.append(u)
        return units
    
    def get_impacted_tiles(self, x, y):
        return [p for stage in CommonContent.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius'), ignore_walls=True) for p in stage]
    
    def make_buff(self, keylist):
        resist_tags = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Dark, Level.Tags.Holy, Level.Tags.Arcane]
        possible_attrs = ['damage', 'range', 'radius']
        buff = Level.Buff()
        buff.buff_type = Level.BUFF_TYPE_BLESS
        buff.name = "Secret Santa"
        buff.color = Level.Tags.Fire.color
        if keylist[0] > .6:
            num_bonuses = math.floor(keylist[1]/.27)
            if num_bonuses < 1:
                num_bonuses = 1
            attrs = random.sample(possible_attrs, num_bonuses)
            for attr in attrs:
                mag = self.get_stat('magnitude')
                if attr == 'range':
                    mag = mag // 3 if mag > 1 else 1
                if attr == 'radius':
                    mag = max(mag//4, 1)
                buff.global_bonuses[attr] = mag
        if keylist[1] > .4:
            num_bonuses = math.floor(keylist[2]/.225)
            if num_bonuses < 1:
                num_bonuses = 1
            resists_final = random.sample(resist_tags, num_bonuses)
            for resist in resists_final:
                buff.resists[resist] = 50
        if keylist[2] > .8:
            elem = random.choice(resist_tags)
            bolt = CommonContent.SimpleRangedAttack(name="Secret Strike", damage=6, damage_type=elem, range=7)
            if keylist[2] >.9:
                bolt.damage *= 2
            buff.spells = [bolt]
        return buff
    
    def get_description(self):
        return (
                "Secretly give each ally in a [{radius}_tile_burst:radius] a buff with random effects.\n"
                "Buffs can give ranged attacks of random elements, increase stats of all existing spells, or give 50 resist to random elements.\n"
                "Most buffs have a magnitude of [{magnitude}:damage], and all buffs last [{duration}_turns:duration].\n"
                "Randomly deal [{damage}:damage] [fire], [ice], [lightning], [dark], [holy], or [arcane] damage to hit enemies.\n"
                ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        dtypes = [Level.Tags.Fire, Level.Tags.Ice, Level.Tags.Lightning, Level.Tags.Dark, Level.Tags.Holy, Level.Tags.Arcane]
        for unit in self.get_targets(x, y):
            if self.caster.level.are_hostile(unit, self.caster):
                dtype = random.choice(dtypes)
                self.caster.level.deal_damage(unit.x, unit.y, self.get_stat('damage'), dtype, self)
            else:
                keys = [random.random() for i in range(3)]
                buff = self.make_buff(keys)
                unit.apply_buff(buff, self.get_stat('duration'))

class ScrollKillBuff(Level.Buff):
    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.color = Level.Tags.Physical.color
        self.spell = spell
        self.name = "Festive Runes"
        self.owner_triggers[Level.EventOnSpellCast] = self.on_cast
        if self.spell.get_stat('paper'):
            self.owner_triggers[Level.EventOnDeath] = self.death_explosion
    
    def on_cast(self, evt):
        self.owner.kill()

    def death_explosion(self, evt):
        for unit in self.owner.level.get_units_in_ball(Level.Point(self.owner.x, self.owner.y), 3):
            if Level.are_hostile(self.owner, unit):
                unit.deal_damage(5, random.choice([Level.Tags.Poison, Level.Tags.Fire]), self)

    def get_tooltip(self):
        return "Dies when casting spells" + ("" if not self.spell.get_stat('paper') else ", dealing [poison] or [fire] damage to nearby enemies.")
    
class WriteHappyScrolls(Level.Spell):

    def on_init(self):
        self.name = "Festive Writings"
        self.range = 0
        self.cool_down = 0
        self.min = self.max = 0
        self.scroll_spawn = None

    def get_description(self):
        return "Summon %d-%d christmas cards" % (self.min, self.max)

    def cast(self, x, y):
        for _ in range(random.randint(self.min, self.max)):
            self.summon(self.scroll_spawn(), sort_dist=False)
            yield

class FestivePen(Level.Spell):
    def on_init(self):
        self.name = "Festive Quill"
        self.level = 4
        self.range = 6
        self.minion_health = 15
        self.max_charges = 3
        self.num_summons = 2
        self.minion_damage = 8
        self.minion_range = 8
        self.must_target_empty = True
        self.tags = [Level.Tags.Ice, Level.Tags.Conjuration]

        self.asset = ["HolidayPack2", "quill_icon"]

        self.upgrades['support'] = (1, 3, "Warm Messages", "The christmas cards' attacks are replaced with a spell that increases allies' damage by 3 for 8 turns.")
        self.upgrades['paper'] = (1, 5, "Colorful Paper", "Christmas cards deal fixed 5 [poison] or [fire] damage randomly to enemies in a 3 tile radius when they die.")
        self.upgrades['guard'] = (1, 4, "Dura-Quill", "The quill regenerates 1 shield per turn, to a maximum of 5.")

    def get_extra_examine_tooltips(self):
        return [self.make_quill(), self.make_scroll()] + self.spell_upgrades
    
    def make_quill(self):
        bomb = Level.Unit()
        bomb.name = "Festive Quill"
        bomb.stationary = bomb.flying = True
        bomb.asset_name = os.path.join("..","..","mods","HolidayPack2","festive_quill")
        bomb.max_hp = self.get_stat('minion_health')
        bomb.shields = 5
        bomb.tags = [Level.Tags.Ice, Level.Tags.Arcane, Level.Tags.Construct]
        for dtype in [Level.Tags.Ice, Level.Tags.Arcane]:
            bomb.resists[dtype] = 75
        bomb.resists[Level.Tags.Fire] = -100
        bomb.buffs.append(CommonContent.TeleportyBuff(8, .15))
        s = WriteHappyScrolls()
        s.max, s.min = self.get_stat('num_summons')+2, self.get_stat('num_summons')-1
        s.cool_down = 5
        s.scroll_spawn = self.make_scroll
        bomb.spells.append(s)
        if self.get_stat('guard'):
            bomb.buffs.append(CommonContent.ShieldRegenBuff(5, 1))
        return bomb
    
    def make_scroll(self):
        scroll = Level.Unit()
        scroll.name = "Christmas Card"
        scroll.asset_name = os.path.join("..","..","mods","HolidayPack2","christmas_scroll")
        scroll.max_hp = 10
        scroll.shields = 1
        scroll.flying = True
        scroll.buffs.append(ScrollKillBuff(self))
        bolt = CommonContent.SimpleRangedAttack(name="Season's Greetings", damage=self.get_stat('minion_damage'), damage_type=Level.Tags.Ice, range=self.get_stat('minion_range'))
        scroll.spells.append(bolt)
        if self.get_stat('support'):
            boost = CommonContent.SimpleCurse(lambda: CommonContent.BloodrageBuff(3), 8)
            boost.range = self.get_stat('minion_range') + 1
            boost.name = "Morale Boost"
            old = boost.can_cast
            boost.can_cast = lambda x, y: old(x, y) and self.caster.level.get_unit_at(x, y).source != self
            scroll.spells.insert(0, boost)
        scroll.source = self
        return scroll
    
    def get_description(self):
        return (
                "Summon a festive quill on target tile."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        self.summon(self.make_quill(), Level.Point(x, y))

class NogPulse(Level.Spell):
    def on_init(self):
        self.level = 5
        self.tags = [Level.Tags.Nature, Level.Tags.Ice, Level.Tags.Sorcery]
        self.name = "Splash of Eggnog"
        self.max_charges = 3
        self.damage = 13
        self.range = 0
        self.radius = 5
        self.duration = 5

        self.asset = ["HolidayPack2", "festive_quill"]

        self.upgrades['channel'] = (1, 5, "Channeling", "Splash of Eggnog can be channeled for up to 7 turns.")
        self.upgrades['refresh'] = (1, 5, "Refreshment", "This spell reduces allies' ability cooldowns by 1 instead of hurting them.")
        self.upgrades['toast'] = (1, 6, "Celebratory Toast", "Allies in line of sight of you who have above 50% HP mimic this spell, but without your upgrades or bonuses.")

    		
    def get_impacted_tiles(self, x, y):
        return [p for stage in Level.Burst(self.caster.level, Level.Point(x, y), self.get_stat('radius')) for p in stage]

    def get_description(self):
        return (
                "Splash some chilled eggnog around, dealing [{damage}:damage] [poison] and [ice] damage in a [{radius}-tile_burst:radius].\n"
                "Hit enemies are [berserked:berserk] for [{duration}_turns:duration]."
        ).format(**self.fmt_dict())
    
    def cast(self, x, y, channel_cast=False):

        if self.get_stat('channel') and not channel_cast:
            self.caster.apply_buff(Level.ChannelBuff(self.cast, Level.Point(x, y)), 7)
            return
        
        else:
            dtypes = [Level.Tags.Poison, Level.Tags.Ice]
            for spread in CommonContent.Burst(self.caster.level, self.caster, self.get_stat('radius')):
                for point in spread:
                    if point.x == self.caster.x and point.y == self.caster.y:
                        continue
                    u = self.caster.level.get_unit_at(point.x, point.y)
                    if u and not Level.are_hostile(u, self.caster) and self.get_stat('refresh'):
                        for s in u.spells:
                            try:
                                u.cool_downs[s] = max(0, u.cool_downs[s]-1)
                            except KeyError:
                                continue
                        continue
                    d = 0
                    for dtype in dtypes:
                        d += self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), dtype, self)
                    if u and Level.are_hostile(u, self.caster) and d > 0:
                        u.apply_buff(Level.BerserkBuff(), self.get_stat('duration'))
                yield
            if self.get_stat('toast'):
                eligibles = [u for u in self.caster.level.get_units_in_los(self.caster) if u.cur_hp/u.max_hp > .5 and not Level.are_hostile(u, self.caster) and u != self.caster]
                for e in eligibles:
                    to_mime = NogPulse()
                    to_mime.caster = to_mime.owner = to_mime.statholder = e
                    self.caster.level.act_cast(e, to_mime, e.x, e.y, pay_costs=False)
            yield


class CookieBuff(Level.Buff):
    def __init__(self, spell, num_hits):
        self.block_pow = spell.get_stat('damage') - (0 if spell.get_stat('auto') else num_hits)
        self.spell = spell
        Level.Buff.__init__(self)

    def on_init(self):
        self.name = "Cookie Satisfaction %d" % self.block_pow
        self.color = Level.Tags.Enchantment.color
        self.buff_type = Level.BUFF_TYPE_BLESS
        self.owner_triggers[Level.EventOnPreDamaged] = self.on_dmg
        self.stack_type = Level.STACK_NONE
        self.owner_triggers[Level.EventOnBuffApply] = self.snickerdoodle

    def snickerdoodle(self, evt):
        if self.spell.get_stat('funny'):
            if evt.buff.buff_type == Level.BUFF_TYPE_BLESS:
                evt.buff.turns_left = math.floor(evt.buff.turns.left*1.25)
    
    def on_dmg(self, evt):
        if evt.damage > 0 and evt.damage < self.block_pow:
            self.owner.add_shields(1)

    def on_advance(self):
        if self.spell.get_stat('funny'):
            self.owner.deal_damage(-3, Level.Tags.Heal, self)

class CookiePass(Level.Spell):
    def on_init(self):
        self.level = 5
        self.tags = [Level.Tags.Enchantment, Level.Tags.Nature]
        self.name = "Cookie Pass"
        self.max_charges = 3
        self.damage = 12
        self.range = 7
        self.requires_los = False
        self.duration = 8
        self.cascade_range = 5

        self.asset = ["HolidayPack2", "festive_quill"]

        self.upgrades['auto'] = (1, 4, "Auto-Refill", "This spell's buff no longer weakens after each cascade.")
        self.upgrades['funny'] = (1, 6, "Snickerdoodles", "Affected allies regenerate 3 HP each turn, and positive effects applied to them last 25% longer, rounded down.")
        self.upgrades['cascade_range'] = (3, 4, "Quick Service")

    def can_cast(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        return u and not Level.are_hostile(u, self.caster) and Level.Spell.can_cast(self, x, y)

    def get_description(self):
        return (
            "Create a magic serving of cookies and milk for your allies.\n"
            "It can move itself up to [{cascade_range}:cascade_range] tiles away for the next ally.\n"
            "Allies affected gain a buff for [{duration}_turns:duration] allowing them to block damage below [{damage}:damage], which weakens by 1 each time an ally is buffed.\n"
            "Allies cannot be targeted more than once by the same casting of this spell, and this effect does not stack."
        ).format(**self.fmt_dict())
    
    def cast(self, x, y):
        unit = self.caster.level.get_unit_at(x, y)
        first_time = True
        targets_hit = 0
        affected = set()

        while unit or first_time:
            if targets_hit >= self.get_stat('damage') and not self.get_stat('auto'):
                break
            if unit:
                unit.apply_buff(CookieBuff(self, targets_hit), self.get_stat('duration'))
                for _ in range(3):
                    yield
                affected.add(unit)
                first_time = False
                targets_hit += 1
                candidates = self.caster.level.get_units_in_los(unit)
                candidates = [c for c in candidates if not Level.are_hostile(c, self.caster) and c != self.caster and c not in affected]
                candidates = [c for c in candidates if Level.distance(c, unit) <= self.get_stat('cascade_range')]
                if candidates:
                    unit = random.choice(candidates)
                else:
                    unit = None
            else:
                unit = None

class Bravery(Level.Buff):
    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.global_triggers[Level.EventOnDamaged] = self.on_damage
        self.color = Level.Tags.Enchantment.color
        self.name = "Bravery"
        self.global_bonuses['damage'] = 1
        self.stack_type = Level.STACK_INTENSITY
        self.resists[Level.Tags.Holy] = spell.get_stat('spirit')

    def on_damage(self, evt):
        if evt.source == self.owner or evt.source.owner == self.owner:
            self.owner.remove_buff(self)
    
    def on_pre_advance(self):
        if not (b := self.spell.caster.get_buff(Level.ChannelBuff)):
            self.owner.remove_buff(self)
        if b.spell != CarolSong().cast:
            self.owner.remove_buff(self)

class CarolSong(Level.Spell):
    def on_init(self):
        self.level = 6
        self.tags = [Level.Tags.Enchantment]
        self.name = "Carol of the Hero"
        self.max_charges = 1
        self.range = 0
        self.radius = 7
        self.turns_passed = 0

        self.asset = ["HolidayPack2", "festive_quill"]

        self.upgrades['spirit'] = (1, 5, "Spirit Song", "Each bravery stack provides a permanent 1% [holy] resistance, which lasts until removed. [Undead] allies with 100 or more [physical] resistance get an extra stack of Bravery.")
        self.upgrades['shatter'] = (1, 4, "Shattering Voice", "Deal a fixed 3 [physical] damage to enemies in the radius each turn.")
        self.upgrades['figgy'] = (1, 5, "Figgy Pudding", "The closest non-poisoned ally in the radius each turn is fully healed.")

    def get_description(self):
        return (
            "Sing a rousing Christmas carol, which can be channeled infinitely.\n"
            "Each turn you channel this spell, allies in a [{radius}-tile_radius:radius] gain stacks of Bravery equal to the number of turns channeled so far.\n"
            "Each stack grants 1 damage to all abilities.\n"
            "Bravery stacks are automatically removed from targets when channeling stops or whenever they successfully deal damage."
        ).format(**self.fmt_dict())
    
    def cast(self, x, y, channel_cast=False):

        if not channel_cast:
            self.caster.apply_buff(Level.ChannelBuff(self.cast, Level.Point(x, y)), 0)
            self.turns_passed = 0
            return
        
        else:
            self.turns_passed += 1
            allies = [u for u in self.caster.level.get_units_in_ball(self.caster, 7) if not Level.are_hostile(u, self.caster) and u != self.caster]
            enemies = [u for u in self.caster.level.get_units_in_ball(self.caster, 7) if Level.are_hostile(u, self.caster)]
            for a in allies:
                if a.resists[Level.Tags.Physical] >= 100 and Level.Tags.Undead in a.tags and self.get_stat('spirit'):
                    a.apply_buff(Bravery(self))
                for _ in range(self.turns_passed):
                    a.apply_buff(Bravery(self))
                    a.deal_damage(0, Level.Tags.Poison, self)
                    yield
            if self.get_stat('figgy'):
                allies = [u for u in allies if not u.has_buff(CommonContent.Poison)]
                random.shuffle(allies)
                if not allies:
                    return
                allies.sort(key=lambda u: Level.distance(u, self.caster))
                cand = allies[0]
                cand.deal_damage(-cand.max_hp, Level.Tags.Heal, self)
            if self.get_stat('shatter'):
                for e in enemies:
                    e.deal_damage(3, Level.Tags.Physical, self)
                    yield


class WreathThrow(Level.Spell):
    def on_init(self):
        self.level = 4
        self.tags = [Level.Tags.Sorcery, Level.Tags.Nature]
        self.name = "Strike Wreath"
        self.max_charges = 6
        self.damage = 20
        self.range = 5
        self.cascade_range = 6
        self.can_target_empty = False
        self.no_friendly_fire = True

        self.asset = ["HolidayPack2", "wreath"]

        self.upgrades['whirl'] = (1, 5, "Wreath Whirl", "The wreath has a 15% chance to perform a critical hit each chain, dealing 7 times damage.")
        self.upgrades['ivy'] = (1, 6, "Ivy Halo", "Each target that survives is [berserked:berserk] for 1 turn, then casts your Poison Sting or Heavenly Blast randomly on the next target if possible.\nThese castings occur once all targets are hit.")
        self.upgrades['regift'] = (2, 6, "Arcane Re-gifting", "Wreaths can pass through walls and hit the same target up to three times.")

    def get_description(self):
        return (
            "Throw a wreath at the target, dealing [{damage}_physical_damage:physical].\n"
            "The wreath will cascade to enemies in [{cascade_range}_tiles:cascade_range] repeatedly until it fails to find a new target.\n"
            "The wreath can hit the same target up to %d time%s." % (1+self.get_stat('regift'), 's' if self.get_stat('regift') else '')
        ).format(**self.fmt_dict())
    
    def cast(self, x, y):
        unit = self.caster.level.get_unit_at(x, y)
        first_time = True
        prev = self.caster
        already_hit = []

        while unit or first_time:
            if unit:
                for p in self.caster.level.get_points_in_line(prev, unit)[1:]:
                    self.caster.level.projectile_effect(p.x, p.y, proj_name=os.path.join("..","..","..","mods","HolidayPack2","wreath"), proj_origin=self.caster, proj_dest=unit)
                dmg = self.get_stat('damage')
                if random.random() < .15 and self.get_stat('whirl'):
                    dmg *= 7
                unit.deal_damage(dmg, Level.Tags.Physical, self)
                already_hit.append(Level.Point(unit.x, unit.y))
                for _ in range(5):
                    yield
                first_time = False
                candidates = self.caster.level.get_units_in_los(unit) if not self.get_stat('regift') else self.caster.level.units
                candidates = [c for c in candidates if Level.are_hostile(c, self.caster) and Level.distance(c, unit) <= self.get_stat('cascade_range') and c != unit]
                candidates = [c for c in candidates if already_hit.count(Level.Point(c.x, c.y)) < 1 + self.get_stat('regift')]
                if candidates:
                    prev = unit
                    unit = random.choice(candidates)
                    sp = random.choice([Spells.PoisonSting, Spells.HolyBlast])()
                    sp.caster = sp.owner = prev
                    sp.statholder = self.caster
                    if sp.can_cast(unit.x, unit.y) and self.get_stat('ivy') and prev.is_alive():
                        prev.apply_buff(Level.BerserkBuff(), 1)
                        self.caster.level.act_cast(prev, sp, unit.x, unit.y, pay_costs=False)
                else:
                    unit = None
            else:
                unit = None

class DecorateBuff(Level.Buff):
    def __init__(self, spell):
        Level.Buff.__init__(self)
        self.color = Level.Tags.Nature.color
        self.spell = spell
        self.name = "Nicely Decorated"
        self.global_triggers[Level.EventOnDamaged] = self.star

    def is_tree(self):
        return any(i in self.owner.name.lower() for i in ["treant", "spriggan", "bark lord"])

    def on_advance(self):
        if self.is_tree():
            self.owner.advance()

    def on_applied(self, owner):
        if self.spell.get_stat('light') and (self.owner.recolor_primary is None or self.owner.recolor_primary != Level.Tags.Lightning.color):
            BossSpawns.apply_modifier(BossSpawns.Stormtouched, self.owner)
            self.owner.spells[0].owner = self.owner.spells[0].caster = self.owner
            self.owner.Anim = None #reset animation so game registers color changes
        b = Monsters.SporeBeastBuff() if self.spell.get_stat('ornaments') else Monsters.SpikeBeastBuff()
        b.damage, b.radius = self.spell.get_stat('damage'), self.spell.get_stat('radius')
        self.owner.apply_buff(b)

    def star(self, evt):
        dmg = 2 + 2*int(self.is_tree())
        if not self.spell.get_stat('star'):
            return
        if evt.source == self.owner or evt.source.owner == self.owner:
            evt.unit.deal_damage(dmg, random.choice([Level.Tags.Arcane, Level.Tags.Holy]), self.spell)
        elif evt.unit == self.owner:
            victim = evt.source if type(evt.source) == Level.Unit else evt.source.owner
            victim.deal_damage(dmg, random.choice([Level.Tags.Arcane, Level.Tags.Holy]), self.spell)

class Treelight(Level.Spell):
    def on_init(self):
        self.level = 5
        self.tags = [Level.Tags.Nature, Level.Tags.Enchantment]
        self.name = "Decoration"
        self.range = 3
        self.max_charges = 2
        self.damage = 16
        self.radius = 2
        self.can_target_empty = False
        self.no_friendly_fire = True

        self.asset = ["HolidayPack2", "festive_quill"]

        self.upgrades['star'] = (1, 6, "Star on Top", "Targets deal fixed 2 [arcane] or [holy] damage to any units they attack or take damage from. Treants, spriggans, and bark lords deal 4 instead.")
        self.upgrades['light'] = (1, 5, "Fancy Lights", "The ally gains [electric:lightning].")
        self.upgrades['ornaments'] = (1, 6, "Spornaments", "Targets have a 30% chance to heal when hit instead.")
    
    def get_description(self):
        return (
                "Coat target ally in fragile decorations.\n"  
                "This gives them a 30% chance to deal [{damage}_physical_damage:physical] to units in a [{radius}-tile_burst:radius] whenever they are hit."      
                "If this spell targets a treant, spriggan, or bark lord, they gain 1 extra action each turn permanently.\n"
                ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        if not (u := self.caster.level.get_unit_at(x, y)):
            return
        u.apply_buff(DecorateBuff(self))

Spells.all_player_spell_constructors.extend([Ornament, PresentBomb, Festivities, SecretSanta, FestivePen, NogPulse, CookiePass, CarolSong, WreathThrow, Treelight])