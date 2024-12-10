print("Lycanthropes Reborn loaded")

import Level, CommonContent, Monsters, BossSpawns, Spells

#the source of the were crash is applying were to other wolves, so lets fix that

def NeoLycanthrope(monster):
    if getattr(monster, 'is_lycanwolf', False): #if its a wolf, just dont bother applying the bossmod
        #the lycan mod doesnt propagate down to the dogs normally because its applied after propagation checks
        #so mucking with how apply_modifier works wouldnt help much
        return
    
    original_sh = monster.shields
    def get_original():
        monster.shields = original_sh
        monster.refresh() #refresh it afterwards to fix that awful invisible unit bug
        return monster

    removed_buffs = []
    for b in list(monster.buffs):
        if Level.EventOnDeath in b.owner_triggers.keys() or isinstance(b, CommonContent.RespawnAs): #monsters have a triggers dict, so use it to make it less annoying and account for on-death buffs added by mods
            #might get goofy with cursed cats and other more niche on death guys but i dont think its an issue
            if b.applied:
                monster.remove_buff(b)
            else:
                monster.buffs.remove(b)
            removed_buffs.append(b)

    def animal_spawn_fn():
        unit = Level.Unit()
        unit.name = "%s Wolf" % monster.name
        unit.asset_name = "wolf"
        unit.max_hp = monster.max_hp // 2

        unit.tags = [Level.Tags.Living, Level.Tags.Dark]
        unit.resists[Level.Tags.Dark] = 50
        unit.is_coward = True

        unit.buffs.append(CommonContent.MatureInto(get_original, 20))
        unit.buffs.extend(removed_buffs)
        unit.recolor_primary = Level.Color(11, 125, 7)
        setattr(unit, 'is_lycanwolf', True) #mark this unit as a lycan wolf
        return unit

    monster.apply_buff(CommonContent.RespawnAs(animal_spawn_fn, name='Wolf'))
    monster.apply_buff(CommonContent.RegenBuff(5))

    adjusted_monster_name = monster.name[0].lower() + monster.name[1:]
    monster.name = "Were%s" % adjusted_monster_name
    monster.recolor_primary =  Level.Color(51, 105, 30)

    if Level.Tags.Dark not in monster.tags:
        monster.tags.append(Level.Tags.Dark)
    if monster.resists[Level.Tags.Dark] <= 50:
        monster.resists[Level.Tags.Dark] = 50

    return monster

BossSpawns.modifiers.append((NeoLycanthrope, 4, 2, lambda m: BossSpawns.check_death_buffs(m))) #drop it in the game, old death buff check is fine since its not like werekitties kill the game

#test spell to repro lycan crash for experimentation
class LycanTest(Level.Spell):
    def on_init(self):
        self.name = "Test Spell"
        self.max_charges = 0
        self.tags = [Level.Tags.Enchantment, Level.Tags.Nature]
        self.range = 50
        self.level = 1
        self.damage = 7
        self.can_target_empty = False

    def get_description(self):
        return (
            "Add were modifier to unit."
        ).format(**self.fmt_dict())
    
    def cast_instant(self, x, y):
        u = self.caster.level.get_unit_at(x, y)
        if not u:
            return
        BossSpawns.apply_modifier(NeoLycanthrope, u)

#Spells.all_player_spell_constructors.extend([LycanTest])

#the way to return stacking jars to the game

# def apply_modifier_new(modifier, unit, propogate=True, apply_hp_bonus=False):
#    BossSpawns.apply_modifier(modifier, unit, propogate, apply_hp_bonus)
#    setattr(unit, modifier.__name__, true) #set a flag with the bossmod's function name (or drop it in a list of bossmods)

#then at jar checks, all dylan has to do is check if the flag is active, if it is, abort jar application


