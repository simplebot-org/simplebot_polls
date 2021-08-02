class TestPlugin:
    def test_new(self, mocker) -> None:
        msg = mocker.get_one_reply(
            """/new
            Do you like polls?
            yes"""
        )
        assert "❌" in msg.text
        msg = mocker.get_one_reply(
            """/new
            Do you like polls?
            yes
            no"""
        )
        assert "❌" not in msg.text

    def test_get(self, mocker) -> None:
        self._create_polls(mocker, 1)
        msg = mocker.get_one_reply("/get_4")
        assert "❌" in msg.text
        msg = mocker.get_one_reply("/get_1")
        assert "❌" not in msg.text
        assert "📊" in msg.text
        assert msg.has_html()
        assert "📊" in msg.html

    def test_status(self, mocker) -> None:
        self._create_polls(mocker, 1)

        # poll creator can see status without voting
        msg = mocker.get_one_reply("/status_1")
        assert "❌" not in msg.text

        # users can't see status until they vote
        addr = "addr2@example.com"
        msg = mocker.get_one_reply("/status_1", addr=addr)
        assert "❌" in msg.text
        mocker.get_one_reply("/vote_1_1", addr=addr)
        msg = mocker.get_one_reply("/status_1", addr=addr)
        assert "❌" not in msg.text

    def test_list(self, mocker) -> None:
        msg = mocker.get_one_reply("/list")
        assert "❌" in msg.text

        self._create_polls(mocker, 1)

        msg = mocker.get_one_reply("/list")
        assert "❌" not in msg.text

    def test_end(self, mocker) -> None:
        self._create_polls(mocker, 2)

        msg = mocker.get_one_reply("/get_1")
        assert "❌" not in msg.text
        msg = mocker.get_one_reply("/list")
        assert "❌" not in msg.text

        msg = mocker.get_one_reply("/vote_1_1", addr="addr2@example.com")
        assert "❌" not in msg.text
        msgs = mocker.get_replies("/end_1")
        assert len(msgs) == 2

        msg = mocker.get_one_reply("/list")
        assert "❌" not in msg.text

        msg = mocker.get_one_reply("/end_2")
        assert "❌" not in msg.text

        msg = mocker.get_one_reply("/get_1")
        assert "❌" in msg.text
        msg = mocker.get_one_reply("/list")
        assert "❌" in msg.text

    def test_vote(self, mocker) -> None:
        self._create_polls(mocker, 1)

        msg = mocker.get_one_reply("/vote_1_10")
        assert "❌" in msg.text
        msg = mocker.get_one_reply("/vote_1_1")
        assert "❌" not in msg.text
        msg = mocker.get_one_reply("/vote_1_1", addr="addr2@example.com")
        assert "❌" not in msg.text
        msg = mocker.get_one_reply("/vote_1_2", addr="addr3@example.com")
        assert "❌" not in msg.text
        msg = mocker.get_one_reply("/vote_1_1", addr="addr3@example.com")
        assert "❌" in msg.text
        msg = mocker.get_one_reply("/vote_2_1")
        assert "❌" in msg.text

    @staticmethod
    def _create_polls(mocker, count) -> None:
        for i in range(count):
            msg = mocker.get_one_reply(
                f"""/new
                Do you like polls? ({i})
                yes
                no
                maybe"""
            )
            assert "❌" not in msg.text
