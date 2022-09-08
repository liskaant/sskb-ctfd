import itertools

from flask import Blueprint
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history
from sqlalchemy import or_, and_

from CTFd.models import Challenges, Solves, Awards, Users, Teams, db, UserFieldEntries, Fields
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.utils.modes import get_model
from CTFd.utils.humanize.numbers import ordinalize
from CTFd.utils.plugins import register_stylesheet, register_admin_stylesheet

from CTFd.api.v1.challenges import ChallengeSolves

class FirstBloodChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "firstblood"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    first_blood_bonus = db.Column(db.JSON)

    def __init__(self, *args, **kwargs):
        # This is kind of a hack because serializeJSON in CTFd does not support arrays
        first_blood_bonus = None
        for attr, value in kwargs.items():
            if attr.startswith('first_blood_bonus'):
                first_blood_bonus = []
        if first_blood_bonus is not None:
            for i in itertools.count():
                attr = 'first_blood_bonus[{0}]'.format(i)
                if attr not in kwargs:
                    break
                first_blood_bonus.append(int(kwargs[attr]) if kwargs[attr] != '' else None)
                del kwargs[attr]
            while first_blood_bonus[-1] is None:
                first_blood_bonus.pop()
            kwargs['first_blood_bonus'] = first_blood_bonus

        super(FirstBloodChallenge, self).__init__(**kwargs)

class FirstBloodAward(Awards):
    __mapper_args__ = {"polymorphic_identity": "firstblood"}
    id = db.Column(
        db.Integer, db.ForeignKey("awards.id", ondelete="CASCADE"), primary_key=True
    )
    solve_id = db.Column(db.Integer, db.ForeignKey("solves.id", ondelete="RESTRICT"))  # It doesn't seem possible to do this well on the database level (FirstBloodAward always gets removed without the base Awards entry), so we do it on the application level
    solve_num = db.Column(db.Integer, nullable=False)

    solve = db.relationship("Solves", foreign_keys="FirstBloodAward.solve_id", lazy="select")

class FirstBloodValueChallenge(BaseChallenge):
    id = "firstblood"  # Unique identifier used to register challenges
    name = "firstblood"  # Name of a challenge type
    templates = {  # Handlebars templates used for each aspect of challenge editing & viewing
        "create": "/plugins/sskb_first_blood/assets/create.html",
        "update": "/plugins/sskb_first_blood/assets/update.html",
        "view": "/plugins/sskb_first_blood/assets/view.html",
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/sskb_first_blood/assets/create.js",
        "update": "/plugins/sskb_first_blood/assets/update.js",
        "view": "/plugins/sskb_first_blood/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/sskb_first_blood/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "firstblood_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = FirstBloodChallenge


    @classmethod
    def read(cls, challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.
        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        data = super().read(challenge)
        data['first_blood_bonus'] = challenge.first_blood_bonus
        return data

    @classmethod
    def update(cls, challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.
        :param challenge:
        :param request:
        :return:
        """

        data = request.form or request.get_json()

        # This is kind of a hack because serializeJSON in CTFd does not support arrays
        first_blood_bonus = None
        for attr, value in data.items():
            if attr.startswith('first_blood_bonus'):
                first_blood_bonus = []
                continue
            setattr(challenge, attr, value)
        if first_blood_bonus is not None:
            for i in itertools.count():
                attr = 'first_blood_bonus[{0}]'.format(i)
                if attr not in data:
                    break
                first_blood_bonus.append(int(data[attr]) if data[attr] != '' else None)
            while first_blood_bonus[-1] is None:
                first_blood_bonus.pop()
            setattr(challenge, 'first_blood_bonus', first_blood_bonus)

        FirstBloodValueChallenge.recalculate_awards(challenge)
        db.session.commit()
        return challenge

    @classmethod
    def delete(cls, challenge):
        """
        This method is used to delete the resources used by a challenge.
        :param challenge:
        :return:
        """
        solve_ids = Solves.query.with_entities(Solves.id).filter_by(challenge_id=challenge.id).subquery()
        award_ids = FirstBloodAward.query.with_entities(FirstBloodAward.id).filter(FirstBloodAward.solve_id.in_(solve_ids)).subquery()
        Awards.query.filter(Awards.id.in_(award_ids)).delete(synchronize_session='fetch')
        super().delete(challenge)

    @classmethod
    def _can_get_award(cls, challenge, solve):
        # No awards for hidden challenges
        if challenge.state != 'visible':
            return False

        # No awards for hidden users
        Model = get_model()
        solver = Model.query.filter_by(id=solve.account_id).first()
        if solver.hidden or solver.banned:
            return False

        return True

    @classmethod
    def _gen_award_data(cls, challenge, solve, solve_num):
        award_points = challenge.first_blood_bonus[solve_num - 1] if (solve_num - 1) < len(challenge.first_blood_bonus) else None
        if award_points is None:
            return None

        return {
            'user_id': solve.user.id if solve.user is not None else None,
            'team_id': solve.team.id if solve.team is not None else None,
            'name': '{0} blood for {1}'.format(ordinalize(solve_num), challenge.name),
            'description': 'Bonus points for being the {0} to solve the challenge'.format(ordinalize(solve_num)),
            'category': 'First Blood',
            'date': solve.date,
            'value': award_points,
            'icon': 'medal-{0}'.format(ordinalize(solve_num)) if solve_num <= 3 else 'medal',
            'solve_id': solve.id,
            'solve_num': solve_num,
        }

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)

        # Get the Solve object that was just inserted by solve() (that method should really return it :<)
        solve = Solves.query.filter(Solves.challenge_id == challenge.id)
        if user is not None:
            solve = solve.filter(Solves.user_id == user.id)
        if team is not None:
            solve = solve.filter(Solves.team_id == team.id)
        solve = solve.first()

        if FirstBloodValueChallenge._can_get_award(challenge, solve):
            # Figure out the solve number
            Model = get_model()

            solve_count = Solves.query.join(Model, Solves.account_id == Model.id)

            if Model == Users:
                category = None
                for field in user.fields:
                    if field.name == 'Category':
                        category = field.value
                        break

                solve_count = (
                    solve_count.join(UserFieldEntries, UserFieldEntries.user_id == Model.id, isouter=True)
                    .join(Fields, and_(
                        Fields.id == UserFieldEntries.field_id,
                        Fields.name == 'Category'
                    ), isouter=True)
                    .filter(UserFieldEntries.value.in_([None, '"' + category + '"']))
                )

            solve_count = (
                solve_count.filter(
                    Solves.id <= solve.id,
                    Solves.challenge_id == challenge.id,
                    Model.hidden == False,
                    Model.banned == False,
                )
                .count()
            )

            # Insert the award into the database
            award_data = FirstBloodValueChallenge._gen_award_data(challenge, solve, solve_count)
            if award_data is not None:
                award = FirstBloodAward(**award_data)
                db.session.add(award)
                db.session.commit()

    @classmethod
    def recalculate_awards(cls, challenge):
        """
        Recalculate all of the awards after challenge has been edited or solves/users were removed
        You have to call db.session.commit() manually after this!
        """
        Model = get_model()

        solves = (
            Solves.query.join(Model, Solves.account_id == Model.id)
            .filter(Solves.challenge_id == challenge.id)
            .order_by(Solves.id)
            .all()
        )

        i = {}
        for solve in solves:
            category = None
            if Model == Users:
                category = (
                    UserFieldEntries.query.join(Fields, and_(
                        Fields.id == UserFieldEntries.field_id,
                        Fields.name == 'Category'
                    ))
                    .filter(UserFieldEntries.user_id == solve.user_id)
                    .first()
                ).value

            award = FirstBloodAward.query.filter(FirstBloodAward.solve_id == solve.id).first()

            if category not in i:
                i[category] = 0

            if FirstBloodValueChallenge._can_get_award(challenge, solve):
                i[category] += 1
                award_data = FirstBloodValueChallenge._gen_award_data(challenge, solve, i[category])
            else:
                award_data = None

            if award_data is not None:
                if award is not None:
                    for k,v in award_data.items():
                        setattr(award, k, v)
                else:
                    award = FirstBloodAward(**award_data)
                    db.session.add(award)
            else:
                if award:
                    db.session.delete(award)


@event.listens_for(Session, "after_bulk_delete")
def after_bulk_delete(delete_context):
    if delete_context.primary_table.name == "solves":
        # A batch delete of solves just occured
        # This usually means that CTFd is removing a user account
        # Why do they do this differently for users and teams? No idea ¯\_(ツ)_/¯

        # Mark ALL first blood challenges for recalculation
        # TODO: It would probably be better to detect which solves got removed and which challenges are affected - but before_bulk_delete doesn't seem to be a thing and the rows are already removed by now
        for challenge in Challenges.query.filter_by(type="firstblood").all():
            FirstBloodValueChallenge.recalculate_awards(challenge)

@event.listens_for(Session, "before_flush")
def before_flush(session, flush_context, instances):
    Model = get_model()

    for instance in session.deleted:
        if isinstance(instance, Solves):
            # A solve has been deleted - delete any awards associated with this solve
            award_ids = FirstBloodAward.query.with_entities(FirstBloodAward.id).filter(FirstBloodAward.solve_id == instance.id).subquery()
            rowcount = Awards.query.filter(Awards.id.in_(award_ids)).delete(synchronize_session='fetch')
            if rowcount > 0:
                # Mark the awards for this challenge for recalculation
                if not hasattr(session, 'requires_award_recalculation'):
                    session.requires_award_recalculation = set()
                session.requires_award_recalculation.add(Challenges.query.get(instance.challenge_id))
        if isinstance(instance, Users):
            # A user has been deleted - mark all challenges where this user had awards for recalculation
            # NOTE: This doesn't seem to be used by CTFd - see after_bulk_delete
            for award in FirstBloodAward.query.join(Users, FirstBloodAward.user_id == Users.id).filter(Users.id == instance.id).all():
                if not hasattr(session, 'requires_award_recalculation'):
                    session.requires_award_recalculation = set()
                session.requires_award_recalculation.add(award.solve.challenge)
                session.delete(award)
        if isinstance(instance, Teams):
            # A team has been deleted - mark all challenges where this team had awards for recalculation
            for award in FirstBloodAward.query.join(Teams, FirstBloodAward.team_id == Teams.id).filter(Teams.id == instance.id).all():
                if not hasattr(session, 'requires_award_recalculation'):
                    session.requires_award_recalculation = set()
                session.requires_award_recalculation.add(award.solve.challenge)
                session.delete(award)

    for instance in session.dirty:
        if session.is_modified(instance):
            if isinstance(instance, Model):
                if get_history(instance, "hidden").has_changes() or get_history(instance, "banned").has_changes():
                    # The user/team hidden state has changed - update awards on all challenges this user has solved
                    for solve in Solves.query.join(Challenges, Solves.challenge_id == Challenges.id).filter(Solves.account_id == instance.id, Challenges.type == "firstblood"):
                        if not hasattr(session, 'requires_award_recalculation'):
                            session.requires_award_recalculation = set()
                        session.requires_award_recalculation.add(solve.challenge)

@event.listens_for(Session, "after_flush_postexec")
def after_flush_postexec(session, flush_context):
    if hasattr(session, 'requires_award_recalculation') and session.requires_award_recalculation:
        # Recalculate any challenges whose awards were invalidated by this commit
        for challenge in session.requires_award_recalculation:
            FirstBloodValueChallenge.recalculate_awards(challenge)
        del session.requires_award_recalculation

def api_solves(challenge_id):
    solves = ChallengeSolves.get(None, challenge_id)
    challenge = Challenges.query.filter(Challenges.id == challenge_id).first()
    Model = get_model()

    if not hasattr(challenge, 'first_blood_bonus'):
        return solves

    i = {}
    for account in solves['data']:
        solve = (Solves.query
            .filter(Solves.challenge_id == challenge_id)
            .filter(Solves.user_id == account['account_id'])
            .first())
        award = FirstBloodAward.query.filter(FirstBloodAward.solve_id == solve.id).first()
        category = None
        if Model == Users:
            category = (
                UserFieldEntries.query.join(Fields, and_(
                    Fields.id == UserFieldEntries.field_id,
                    Fields.name == 'Category'
                ))
                .filter(UserFieldEntries.user_id == solve.user_id)
                .first()
            ).value

        if category not in i:
            i[category] = 0

        if FirstBloodValueChallenge._can_get_award(challenge, solve):
            i[category] += 1
            award_data = FirstBloodValueChallenge._gen_award_data(challenge, solve, i[category])
        else:
            award_data = None

        if award_data:
            award_data['fb_category'] = category
            account['award'] = award_data

    return solves

def load(app):
    app.db.create_all()
    app.jinja_env.filters.update(ordinalize=ordinalize)
    CHALLENGE_CLASSES["firstblood"] = FirstBloodValueChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/sskb_first_blood/assets/"
    )
    register_stylesheet("/plugins/sskb_first_blood/assets/award-icons.css")
    register_admin_stylesheet("/plugins/sskb_first_blood/assets/award-icons.css")

    app.view_functions['api.challenges_challenge_solves'] = api_solves
