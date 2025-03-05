import Level, Game, RareMonsters, Spells
import inspect, os

frm = inspect.stack()[-1]
RiftWizard = inspect.getmodule(frm[0])

#mt spell wizardry (credit to Bord Listian, i couldnt have done it myself)

def has_enough_targets(self):
	return True

Level.Spell.has_enough_targets = has_enough_targets

__spell_init_old = Level.Spell.__init__

def spell_init(self, *args, **kwargs):
	__spell_init_old(self, *args, **kwargs)
	
	self.multi_targets = []

Level.Spell.__init__ = spell_init

__game_try_cast_old = Game.Game.try_cast

def try_cast(self, spell, x, y, *args, **kwargs):
	if spell.can_cast(x, y):
		spell.multi_targets.append(Level.Point(x, y)) #Append a target
		if(spell.has_enough_targets()):
			return __game_try_cast_old(self, spell, x, y, *args, **kwargs)
		else:
			return True
	else:
		return False
	
Game.Game.try_cast = try_cast
	
def cast_cur_spell(self):
	success = self.game.try_cast(self.cur_spell, self.cur_spell_target.x, self.cur_spell_target.y)
	has_enough_targets = self.cur_spell.has_enough_targets()
	if not success:
		self.play_sound('menu_abort')
	elif not has_enough_targets:
		self.play_sound('menu_confirm')
	#if self.examine_target == self.cur_spell:
		#self.examine_target = None
	if not success or has_enough_targets:
		self.cur_spell = None
		unit = self.game.cur_level.get_unit_at(self.cur_spell_target.x, self.cur_spell_target.y)
		if unit:
			self.cur_spell_target = unit
	
RiftWizard.PyGameView.cast_cur_spell = cast_cur_spell #override completely
	
__pygameview_choose_spell_old = RiftWizard.PyGameView.choose_spell

def choose_spell(self, spell):
	__pygameview_choose_spell_old(self, spell)
	spell.multi_targets = [] #reset targets

RiftWizard.PyGameView.choose_spell = choose_spell

#make the tag and fix it
ltag = Level.Tag("Locking", Level.Color(104,200,14))
RiftWizard.tag_keys['g'] = ltag
Level.Tags.elements.append(ltag)
RiftWizard.tooltip_colors['locking'] = RiftWizard.tooltip_colors['lock_cap'] = ltag.color

#core func for getting all locked units
get_locked = lambda l: [u for u in l.units if u.has_buff(Locked)]

lock_cap_infobox = "The lock cap is how many units can be locked onto at any given time. The lock cap usually cannot be exceeded, except by certain spells."
lock_infobox = "[Locked:locking] does not do anything, but determines the targets of most [locking] spells."

class Locked(Level.Buff):
	def on_init(self):
		self.name = "Locked"
		self.asset = ["LockPack", "assets", "lock_buff"]
		self.color = ltag.color
		self.buff_type = Level.BUFF_TYPE_CURSE
		self.stack_type = Level.STACK_NONE

init_old = Level.Unit.__init__
def unit_init(self, *args, **kwargs):
	init_old(self, *args, **kwargs)
	self.lock_cap = 2
Level.Unit.__init__ = unit_init