package com.llmquality.baseline.entity;

import com.llmquality.baseline.enums.AddressType;
import jakarta.persistence.*;

import java.util.Objects;

@Entity
@Table(name = "addresses")
public class Address {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false)
    private String street;

    @Column(nullable = false)
    private String houseNumber;

    @Column(nullable = false)
    private String postalCode;

    @Column(nullable = false)
    private String city;

    @Column(nullable = false)
    private String country;

    @Enumerated(EnumType.STRING)
    private AddressType addressType = AddressType.PRIVATE;


    public AddressType getAddressType() {
        return addressType;
    }

    public void setAddressType(AddressType addressType) {
        this.addressType = addressType;
    }

    public String getCountry() {
        return country;
    }

    public void setCountry(String country) {
        this.country = country;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getPostalCode() {
        return postalCode;
    }

    public void setPostalCode(String postalCode) {
        this.postalCode = postalCode;
    }

    public String getHouseNumber() {
        return houseNumber;
    }

    public void setHouseNumber(String houseNumber) {
        this.houseNumber = houseNumber;
    }

    public String getStreet() {
        return street;
    }

    public void setStreet(String street) {
        this.street = street;
    }

    public User getUser() {
        return user;
    }

    public void setUser(User user) {
        this.user = user;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    @Override
    public boolean equals(Object o) {
        if (!(o instanceof Address address)) return false;
        return Objects.equals(id, address.id) && Objects.equals(user, address.user) && Objects.equals(street, address.street) && Objects.equals(houseNumber, address.houseNumber) && Objects.equals(postalCode, address.postalCode) && Objects.equals(city, address.city) && Objects.equals(country, address.country) && Objects.equals(addressType, address.addressType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, user, street, houseNumber, postalCode, city, country, addressType);
    }
}

