import unittest
from app import create_app, db
from app.models import User, Post, Role


class PostModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        User.create_deleted_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_new_post(self):
        u = User(username='john', email='john@example.com', password='cat')
        p = Post(title='This is a test title', body='# **body** of *the post*', author=u)
        db.session.add_all([u, p])
        db.session.commit()
        self.assertTrue(p.title == 'This is a test title')
        self.assertTrue(p.body == '# **body** of *the post*')
        # test markdown
        self.assertTrue(p.body_html == '<h1><strong>body</strong> of <em>the post</em></h1>')
        # test auto self upvote
        self.assertTrue(p.vote_count == 1)
        self.assertEqual(p.votes.all()[-1].user, u)

    def test_delete_post(self):
        u = User(username='john', email='john@example.com', password='cat')
        p = Post(title='This is a test title', body='# **body** of *the post*', author=u)
        db.session.add_all([u, p])
        db.session.commit()
        self.assertTrue(p.editable is True)
        self.assertTrue(p.deleted is not True)
        p.deleted = True
        self.assertTrue(p.body == '**[deleted]**')
        self.assertFalse(p.author == u)
        self.assertTrue(p.editable is False)
