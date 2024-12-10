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


class TrickBagSpell(Level.Spell):
    def __init__(self, to_cast, upgrs):
        Level.Spell.__init__(self)
        self.to_cast = to_cast
        self.upgrs = upgrs
        self.range = self.to_cast.range
        
    def on_init(self):
        self.name = "Bag of Tricks Spell"
        
    def can_cast(self, x, y):
        cln = type(self.to_cast)()
        cln.statholder = cln.caster = cln.owner = self.caster
        to_remove = []
        for u in self.upgrs:
            print(u)
            if not any(b.prereq == type(self.to_cast) and b.name == u.name for b in self.caster.buffs):
                self.caster.apply_buff(u)
                to_remove.append(u)
        castbool = cln.can_cast(x, y)
        for b in to_remove:
            self.caster.remove_buff(b)
        return castbool

    def cast(self, x, y):
        cln = type(self.to_cast)()
        cln.statholder = cln.caster = cln.owner = self.caster
        to_remove = []
        for u in self.upgrs:
            if not any(b.prereq == type(self.to_cast) and b.name == u.name for b in self.caster.buffs):   
                self.caster.apply_buff(u)
                to_remove.append(u)
        self.caster.level.act_cast(self.caster, cln, x, y, pay_costs=False)
        def clns():
            for b in to_remove:
                self.caster.remove_buff(b)
            yield
        self.caster.level.queue_spell(clns())
        yield

def trickbag():
    sp = random.choice(Spells.all_player_spell_constructors)()
    up = random.sample(sp.spell_upgrades, random.randint(1, len(sp.spell_upgrades)-1))
    it = Level.Item()
    it.set_spell(TrickBagSpell(sp, up))
    it.description = "Casts %s on use\nHas the following upgrades:\n" % sp.name
    it.name = "Bag of Tricks"
    it.asset = ["TrickBag", "bag_of_trouble"]
    for u in up:
        it.description += "%s\n" % u.name
    return it

Consumables.all_consumables.append((trickbag, Consumables.COMMON))