package com.llmquality.baseline.repository;

import java.util.List;

import com.llmquality.baseline.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;


@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    List<User> findByName(String name);

    boolean existsByName(String name);

}